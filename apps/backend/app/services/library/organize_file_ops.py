from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.db.models.organize import OrganizeAction, OrganizePlan
from app.repositories.library_organize.repository import LibraryOrganizeRepository
from app.repositories.library_roots.repository import LibraryRootRepository
from app.repositories.source.repository import SourceRepository
from app.services.library.path_safety import is_path_within, path_key

PATH_LENGTH_WARNING = 240


class OrganizeFileOps:
    """Low-level filesystem operations for organize plans.

    Handles mkdir, move/rename, write_asset_yaml, backup_asset_yaml,
    and write_asset_yaml_update actions on the filesystem.
    """

    def __init__(
        self,
        repository: LibraryOrganizeRepository | None = None,
        source_repository: SourceRepository | None = None,
        library_root_repository: LibraryRootRepository | None = None,
    ) -> None:
        self.repository = repository or LibraryOrganizeRepository()
        self.source_repository = source_repository or SourceRepository()
        self.library_root_repository = library_root_repository or LibraryRootRepository()

    def execute_action(
        self,
        session: Session,
        action: OrganizeAction,
        preflight_check,
    ) -> tuple[str | None, str | None]:
        """Execute a single filesystem action.

        Runs a preflight safety check first, then dispatches to the
        appropriate handler based on action.action_type.

        Returns (source_path, target_path) on success.
        """
        conflict_status, conflict_message = preflight_check(session, action, set())
        if conflict_status in {"blocked", "stale"}:
            raise RuntimeError(conflict_message or "Action failed pre-execution safety check.")

        if action.action_type == "mkdir":
            return self._execute_mkdir(action)
        if action.action_type in {"move", "rename"}:
            return self._execute_move_rename(action)
        if action.action_type == "write_asset_yaml":
            return self._execute_write_asset_yaml(action)
        if action.action_type == "backup_asset_yaml":
            return self._execute_backup_asset_yaml(action)
        if action.action_type == "write_asset_yaml_update":
            return self._execute_write_asset_yaml_update(session, action)
        raise RuntimeError(f"Unsupported action type: {action.action_type}.")

    # ------------------------------------------------------------------
    # Individual action handlers
    # ------------------------------------------------------------------

    def _execute_mkdir(self, action: OrganizeAction) -> tuple[None, str]:
        target = self.required_target(action)
        if target.exists() and target.is_dir():
            return None, str(target)
        target.mkdir(parents=True, exist_ok=False)
        return None, str(target)

    def _execute_move_rename(self, action: OrganizeAction) -> tuple[str, str]:
        source = self.required_source(action)
        target = self.required_target(action)
        if target.exists():
            raise RuntimeError("Target path already exists and would be overwritten.")
        shutil.move(str(source), str(target))
        if source.exists() or not target.exists():
            raise RuntimeError("Filesystem move did not finish in the expected state.")
        return str(source), str(target)

    def _execute_write_asset_yaml(self, action: OrganizeAction) -> tuple[None, str]:
        target = self.required_target(action)
        if target.exists():
            raise RuntimeError("asset.yaml already exists and will not be overwritten.")
        payload = self.render_asset_yaml(action.payload_json)
        tmp_path = target.with_name(f"{target.name}.tmp-{uuid.uuid4().hex}")
        try:
            tmp_path.write_text(payload, encoding="utf-8")
            if target.exists():
                raise RuntimeError("asset.yaml appeared before final write; refusing to overwrite.")
            os.replace(tmp_path, target)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
        return None, str(target)

    def _execute_backup_asset_yaml(self, action: OrganizeAction) -> tuple[str, str]:
        source = self.required_source(action)
        target = self.required_target(action)
        if target.exists():
            raise RuntimeError("Backup target path already exists.")
        shutil.copy2(str(source), str(target))
        return str(source), str(target)

    def _execute_write_asset_yaml_update(self, session: Session, action: OrganizeAction) -> tuple[str, str]:
        source = self.required_source(action)
        target = self.required_target(action)
        if not source.exists():
            raise RuntimeError("Source asset.yaml no longer exists.")
        if not target.exists():
            raise RuntimeError("Target asset.yaml no longer exists.")
        payload = json.loads(action.payload_json or "{}")
        merged_yaml = payload.get("merged_yaml")
        if not merged_yaml:
            raise RuntimeError("merged_yaml is missing from payload.")
        plan = self.repository.get_plan(session, action.plan_id)
        if plan is None:
            raise RuntimeError("Plan not found.")
        all_actions = self.repository.list_plan_actions(session, action.plan_id)
        backup_actions = [a for a in all_actions if a.action_type == "backup_asset_yaml" and a.action_order < action.action_order]
        if not backup_actions:
            raise RuntimeError("No preceding backup_asset_yaml action found.")
        backup_succeeded = any(a.status == "succeeded" for a in backup_actions)
        if not backup_succeeded:
            raise RuntimeError("Preceding backup_asset_yaml action has not succeeded.")
        rendered = yaml.safe_dump(merged_yaml, allow_unicode=True, sort_keys=False)
        tmp_path = target.with_name(f"{target.name}.tmp-{uuid.uuid4().hex}")
        try:
            tmp_path.write_text(rendered, encoding="utf-8")
            os.replace(tmp_path, target)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
        return str(source), str(target)

    # ------------------------------------------------------------------
    # Path / content helpers
    # ------------------------------------------------------------------

    @staticmethod
    def required_source(action: OrganizeAction) -> Path:
        if not action.source_path:
            raise RuntimeError("Action source_path is required.")
        return Path(action.source_path).resolve()

    @staticmethod
    def required_target(action: OrganizeAction) -> Path:
        if not action.target_path:
            raise RuntimeError("Action target_path is required.")
        return Path(action.target_path).resolve()

    @staticmethod
    def parent_available(target: Path, planned_dirs: set[str]) -> bool:
        return target.parent.exists() or path_key(target.parent) in planned_dirs

    @staticmethod
    def render_asset_yaml(payload_json: str | None) -> str:
        if not payload_json:
            raise RuntimeError("asset.yaml draft payload is missing.")
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError as error:
            raise RuntimeError("asset.yaml draft payload is not valid JSON.") from error
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

    def resolve_root_for_mkdir_or_asset(self, session: Session, path: Path, plan: OrganizePlan | None) -> Path | None:
        """Resolve the enabled source or managed library root that contains *path*.

        If *plan* has a *target_library_root_id* that contains *path*,
        returns that root. Otherwise falls back to scanning enabled sources
        and then enabled library roots.
        """
        if plan is not None and plan.target_library_root_id is not None:
            lib_root = self.library_root_repository.get_by_id(session, plan.target_library_root_id)
            if lib_root and lib_root.is_enabled:
                root_path = Path(lib_root.root_path).resolve()
                if is_path_within(path, root_path):
                    return root_path
            return None
        for source in self.source_repository.list_sources(session):
            if source.is_enabled:
                source_root = Path(source.path).resolve()
                if is_path_within(path, source_root):
                    return source_root
        for lib_root in self.library_root_repository.list_enabled(session):
            root_path = Path(lib_root.root_path).resolve()
            if is_path_within(path, root_path):
                return root_path
        return None
