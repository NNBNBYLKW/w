import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.api.schemas.source import SourceCreateRequest, SourceResponse, SourceUpdateRequest, TriggerScanResponse
from app.core.errors.exceptions import ConflictError, NotFoundError
from app.db.models.source import Source
from app.db.models.task import Task
from app.repositories.source.repository import SourceRepository
from app.services.scanning.service import ScanningService
from app.services.tasks.service import TaskService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SourceManagementService:
    def __init__(self) -> None:
        self.source_repository = SourceRepository()
        self.task_service = TaskService()
        self.scanning_service = ScanningService()

    def list_sources(self, session: Session) -> list[SourceResponse]:
        sources = self.source_repository.list_sources(session)
        latest_tasks_by_source_id = self.task_service.list_latest_scan_tasks_by_source_ids(
            session,
            [source.id for source in sources],
        )
        return [
            self._build_source_response(source, latest_tasks_by_source_id.get(source.id))
            for source in sources
        ]

    def create_source(self, session: Session, payload: SourceCreateRequest) -> SourceResponse:
        canonical_path = self._canonicalize_source_path(payload.path)
        if not canonical_path:
            raise ConflictError("INVALID_SOURCE_PATH", "Source path cannot be empty.")
        self._ensure_source_root_allowed(session, canonical_path)
        now = _utcnow()
        source = Source(
            path=canonical_path,
            display_name=payload.display_name,
            is_enabled=True,
            scan_mode="manual_plus_basic_incremental",
            last_scan_at=None,
            last_scan_status=None,
            created_at=now,
            updated_at=now,
        )
        self.source_repository.add(session, source)
        session.commit()
        session.refresh(source)
        return self._build_source_response(source)

    def update_source(self, session: Session, source_id: int, payload: SourceUpdateRequest) -> SourceResponse:
        source = self.source_repository.get_by_id(session, source_id)
        if source is None:
            raise NotFoundError("SOURCE_NOT_FOUND", "Source not found.")
        canonical_path = self._canonicalize_source_path(source.path)
        self._ensure_source_root_allowed(session, canonical_path, exclude_source_id=source.id)
        source.path = canonical_path
        if payload.display_name is not None:
            source.display_name = payload.display_name
        if payload.is_enabled is not None:
            source.is_enabled = payload.is_enabled
        source.updated_at = _utcnow()
        session.commit()
        session.refresh(source)
        latest_task = self.task_service.list_latest_scan_tasks_by_source_ids(session, [source.id]).get(source.id)
        return self._build_source_response(source, latest_task)

    def delete_source(self, session: Session, source_id: int) -> None:
        source = self.source_repository.get_by_id(session, source_id)
        if source is None:
            raise NotFoundError("SOURCE_NOT_FOUND", "Source not found.")
        self.source_repository.delete(session, source)
        session.commit()

    def trigger_scan(self, session: Session, source_id: int) -> TriggerScanResponse:
        source = self.source_repository.get_by_id(session, source_id)
        if source is None:
            raise NotFoundError("SOURCE_NOT_FOUND", "Source not found.")
        active_task = self.task_service.get_active_scan_task_for_source(session, source_id)
        if active_task is not None:
            raise ConflictError("SCAN_ALREADY_RUNNING", "A scan is already running for this source.")
        task = self.task_service.create_pending_scan_task(session, source_id)
        task = self.scanning_service.run_source_scan_inline(session, source, task)
        return TriggerScanResponse(task_id=task.id, status=task.status)

    def _build_source_response(self, source: Source, latest_scan_task: Task | None = None) -> SourceResponse:
        return SourceResponse(
            id=source.id,
            path=source.path,
            display_name=source.display_name,
            is_enabled=source.is_enabled,
            scan_mode=source.scan_mode,
            last_scan_at=source.last_scan_at,
            last_scan_status=source.last_scan_status,
            last_scan_error_message=self._derive_last_scan_error_message(latest_scan_task),
            created_at=source.created_at,
            updated_at=source.updated_at,
        )

    def _derive_last_scan_error_message(self, latest_scan_task: Task | None) -> str | None:
        if latest_scan_task is None:
            return None
        if latest_scan_task.status != "failed":
            return None
        return latest_scan_task.error_message

    def _canonicalize_source_path(self, raw_path: str) -> str:
        candidate = raw_path.strip()
        if not candidate:
            return ""
        canonical = Path(candidate).resolve(strict=False)
        return os.path.normpath(str(canonical))

    def _ensure_source_root_allowed(
        self,
        session: Session,
        candidate_path: str,
        exclude_source_id: int | None = None,
    ) -> None:
        candidate_parts = self._normalized_path_parts(candidate_path)
        for existing_source in self.source_repository.list_sources(session):
            if exclude_source_id is not None and existing_source.id == exclude_source_id:
                continue

            existing_canonical_path = self._canonicalize_source_path(existing_source.path)
            existing_parts = self._normalized_path_parts(existing_canonical_path)

            if candidate_parts == existing_parts:
                raise ConflictError("SOURCE_ALREADY_EXISTS", "Source path already exists.")
            if self._paths_overlap(candidate_parts, existing_parts):
                raise ConflictError(
                    "SOURCE_ROOT_OVERLAP",
                    "Overlapping source roots are not supported in Phase 1A.",
                )

    def _normalized_path_parts(self, canonical_path: str) -> tuple[str, ...]:
        normalized = os.path.normcase(os.path.normpath(canonical_path))
        return tuple(Path(normalized).parts)

    def _paths_overlap(self, left: tuple[str, ...], right: tuple[str, ...]) -> bool:
        shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
        return shorter == longer[: len(shorter)]
