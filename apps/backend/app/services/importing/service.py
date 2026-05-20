from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePath
from typing import Any

from sqlalchemy.orm import Session

from app.core.classification import classify_file
from app.db.models.file import File
from app.db.models.source import Source
from app.repositories.importing.repository import ImportRepository
from app.repositories.library_roots.repository import LibraryRootRepository
from app.services.importing.object_boundary import (
    ObjectBoundaryResult,
    detect_object_type,
)


_FILE_KIND_TO_TYPE: dict[str, str] = {
    "image": "image",
    "video": "video",
    "audio": "audio",
    "document": "document",
    "ebook": "document",
    "archive": "archive",
    "executable": "other",
    "installer": "other",
    "shortcut": "other",
    "other": "other",
}


@dataclass(frozen=True)
class LibraryV2Capability:
    status: str = "data_foundation"
    import_enabled: bool = False
    inbox_enabled: bool = False


@dataclass
class ImportFileResult:
    source_path: str
    inbox_path: str
    file_id: int | None = None
    inbox_item_id: int | None = None
    status: str = "ok"


@dataclass
class ImportFilesResponse:
    batch_id: int
    created_items: list[dict[str, Any]] = field(default_factory=list)
    failed_items: list[dict[str, Any]] = field(default_factory=list)


class ImportService:
    def __init__(self) -> None:
        self.repository = ImportRepository()
        self.root_repo = LibraryRootRepository()

    # ── capability ──────────────────────────────────────────

    def get_capability(self) -> LibraryV2Capability:
        return LibraryV2Capability()

    # ── batch CRUD ──────────────────────────────────────────

    def create_import_batch(
        self, session: Session, *, source_kind: str = "file_selection", import_method: str = "copy"
    ):
        if import_method != "copy":
            raise ValueError("Only copy import is supported.")
        return self.repository.create_batch(
            session, source_kind=source_kind, import_method=import_method
        )

    def get_import_batch(self, session: Session, batch_id: int):
        return self.repository.get_batch(session, batch_id)

    def list_import_batches(self, session: Session, *, page: int = 1, page_size: int = 50):
        return self.repository.list_batches(session, page=page, page_size=page_size)

    # ── inbox items ─────────────────────────────────────────

    def list_inbox_items(
        self,
        session: Session,
        *,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        batch_id: int | None = None,
    ):
        from app.repositories.importing.repository import InboxItemFilters

        filters = InboxItemFilters(
            page=page, page_size=page_size, status=status, batch_id=batch_id
        )
        return self.repository.list_inbox_items(session, filters=filters)

    def get_inbox_item(self, session: Session, item_id: int):
        return self.repository.get_inbox_item(session, item_id)

    # ── import files ────────────────────────────────────────

    def import_files_to_batch(
        self, session: Session, *, batch_id: int, paths: list[str]
    ) -> ImportFilesResponse:
        batch = self.repository.get_batch(session, batch_id)
        if batch is None:
            raise ValueError(f"Import batch not found: {batch_id}")

        target_root = self._resolve_inbox_root(session)
        managed_source = self._get_managed_source(session)
        inbox_dir = self._ensure_inbox_dir(target_root.root_path, batch_id)

        self.repository.update_batch_status(session, batch, "running")

        created: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []

        for source_path_str in paths:
            op_id = str(uuid.uuid4())
            try:
                result = self._copy_one_file(
                    session,
                    batch,
                    source_path_str,
                    inbox_dir,
                    managed_source.id,
                    target_root.id,
                    op_id,
                )
                created.append({
                    "source_path": result.source_path,
                    "inbox_path": result.inbox_path,
                    "file_id": result.file_id,
                    "inbox_item_id": result.inbox_item_id,
                })
            except Exception as exc:
                failed.append({"path": source_path_str, "error": str(exc)})
                self.repository.append_journal_entry(
                    session,
                    operation_id=op_id,
                    operation_type="import_copy",
                    entity_type="inbox_item",
                    status="failed",
                    error_message=str(exc),
                )

        total = len(created) + len(failed)
        if failed and created:
            final_status = "completed_with_errors"
        elif failed and not created:
            final_status = "failed"
        else:
            final_status = "completed"

        error_summary = json.dumps(failed) if failed else None
        self.repository.update_batch_counts(
            session,
            batch,
            file_count=total,
            completed_count=len(created),
            failed_count=len(failed),
        )
        self.repository.update_batch_status(
            session, batch, final_status, error_summary=error_summary
        )

        return ImportFilesResponse(
            batch_id=batch_id,
            created_items=created,
            failed_items=failed,
        )

    # ── import folder ───────────────────────────────────────

    def import_folder_to_batch(
        self,
        session: Session,
        *,
        batch_id: int,
        folder_path: str,
        mode: str = "object",
    ) -> dict[str, Any]:
        """Import a folder as an object (default) or as loose files."""
        if mode not in {"object", "loose_files"}:
            raise ValueError("mode must be 'object' or 'loose_files'")

        batch = self.repository.get_batch(session, batch_id)
        if batch is None:
            raise ValueError(f"Import batch not found: {batch_id}")

        source = Path(folder_path).resolve()
        if not source.exists():
            raise FileNotFoundError(f"Source folder not found: {folder_path}")
        if not source.is_dir():
            raise ValueError(f"Source path is not a folder: {folder_path}")

        target_root = self._resolve_inbox_root(session)
        managed_source = self._get_managed_source(session)

        # compute target inbox folder with no-overwrite suffix
        inbox_parent = self._ensure_inbox_dir(target_root.root_path, batch_id)
        inbox_folder = self._no_overwrite_target(inbox_parent / source.name)

        self.repository.update_batch_status(session, batch, "running")
        op_id = str(uuid.uuid4())

        try:
            self.repository.append_journal_entry(
                session,
                operation_id=op_id,
                operation_type="import_copy",
                entity_type="import_batch",
                entity_id=batch.id,
                status="started",
                before_json=json.dumps({"source_folder": str(source)}),
                after_json=json.dumps({"target_folder": str(inbox_folder)}),
            )

            # recursive copy
            copied_files = self._copy_folder_to_inbox(source, inbox_folder)

            if mode == "object":
                result = self._create_object_from_folder(
                    session, batch, source, inbox_folder, copied_files,
                    managed_source.id, target_root.id, op_id,
                )
            else:
                result = self._create_loose_items_from_folder(
                    session, batch, source, copied_files,
                    managed_source.id, target_root.id, op_id,
                )

            self.repository.append_journal_entry(
                session,
                operation_id=op_id,
                operation_type="import_copy",
                entity_type="import_batch",
                entity_id=batch.id,
                status="succeeded",
                after_json=json.dumps({"mode": mode, "files_copied": len(copied_files)}),
            )

            self.repository.update_batch_counts(
                session, batch,
                file_count=len(copied_files),
                completed_count=len(copied_files),
                failed_count=0,
            )
            self.repository.update_batch_status(session, batch, "completed")
            return result

        except Exception as exc:
            self.repository.append_journal_entry(
                session,
                operation_id=op_id,
                operation_type="import_copy",
                entity_type="import_batch",
                entity_id=batch.id,
                status="failed",
                error_message=str(exc),
            )
            self.repository.update_batch_status(
                session, batch, "failed", error_summary=str(exc)
            )
            raise

    @staticmethod
    def _copy_folder_to_inbox(source: Path, dest: Path) -> list[tuple[Path, Path]]:
        """Recursively copy folder contents. Returns list of (source_file, dest_file)."""
        copied: list[tuple[Path, Path]] = []
        dest.mkdir(parents=True, exist_ok=True)

        for item in sorted(source.iterdir()):
            if item.is_file():
                target = ImportService._no_overwrite_target(dest / item.name)
                tmp = target.with_name(f".tmp-{uuid.uuid4().hex[:8]}-{target.name}")
                try:
                    shutil.copy2(str(item), str(tmp))
                    tmp.replace(target)
                    copied.append((item, target))
                except Exception:
                    if tmp.exists():
                        tmp.unlink(missing_ok=True)
                    raise
            elif item.is_dir():
                sub_dest = ImportService._no_overwrite_target(dest / item.name)
                sub_copied = ImportService._copy_folder_to_inbox(item, sub_dest)
                copied.extend(sub_copied)

        return copied

    def _create_object_from_folder(
        self,
        session: Session,
        batch: Any,
        source_folder: Path,
        inbox_folder: Path,
        copied_files: list[tuple[Path, Path]],
        managed_source_id: int,
        target_root_id: int,
        operation_id: str,
    ) -> dict[str, Any]:
        """Create object candidate + members from a folder import."""
        # collect relative member paths for detection
        member_rel_paths = [
            str(dest.relative_to(inbox_folder)) for _src, dest in copied_files
        ]
        detection = detect_object_type(inbox_folder.name, member_rel_paths)

        # create object candidate
        reason_json = json.dumps({
            "signals": detection.signals,
            "member_count": len(copied_files),
        })
        obj_candidate = self.repository.create_object_candidate(
            session,
            import_batch_id=batch.id,
            source_root_path=str(source_folder),
            inbox_root_path=str(inbox_folder),
            suggested_object_type=detection.suggested_object_type,
            confidence=detection.confidence,
            member_count=len(copied_files),
            reason_json=reason_json,
        )
        obj_candidate.status = "pending_review"

        # register each file and create inbox_item + object_member
        member_items: list[dict[str, Any]] = []
        for src_file, dest_file in copied_files:
            rel_path = str(dest_file.relative_to(inbox_folder))
            file_record = self._register_imported_file(
                session, src_file, dest_file, managed_source_id
            )
            classification = classify_file(
                dest_file.suffix.lstrip(".") if dest_file.suffix else None,
                str(dest_file),
            )
            inbox_item = self.repository.create_inbox_item(
                session,
                import_batch_id=batch.id,
                file_id=file_record.id,
                source_path=str(src_file),
                inbox_path=str(dest_file),
                status="imported",
                detected_file_kind=classification.file_kind,
                detected_placement=classification.auto_placement,
                target_library_root_id=target_root_id,
            )
            file_record.inbox_item_id = inbox_item.id

            # determine member role from detection
            role_info = detection.member_roles.get(rel_path)
            role = role_info.role if role_info else "unknown_child"
            role_confidence = role_info.confidence if role_info else "low"
            role_reason = role_info.reason if role_info else ""

            self.repository.create_object_member(
                session,
                import_object_candidate_id=obj_candidate.id,
                inbox_item_id=inbox_item.id,
                role=role,
                confidence=role_confidence,
                reason=role_reason,
            )
            member_items.append({
                "relative_path": rel_path,
                "file_id": file_record.id,
                "inbox_item_id": inbox_item.id,
                "role": role,
            })

        # set launch/cover file references
        if detection.launch_candidate_path:
            for item in member_items:
                if item["relative_path"] == detection.launch_candidate_path:
                    obj_candidate.launch_file_id = item["file_id"]
                    break
        if detection.cover_candidate_path:
            for item in member_items:
                if item["relative_path"] == detection.cover_candidate_path:
                    obj_candidate.primary_file_id = item["file_id"]
                    break

        session.flush()

        # journal
        self.repository.append_journal_entry(
            session,
            operation_id=operation_id,
            operation_type="inbox_status_change",
            entity_type="import_object_candidate",
            entity_id=obj_candidate.id,
            status="succeeded",
            after_json=json.dumps({
                "suggested_type": detection.suggested_object_type,
                "confidence": detection.confidence,
                "member_count": len(copied_files),
            }),
        )

        return {
            "object_candidate_id": obj_candidate.id,
            "suggested_object_type": detection.suggested_object_type,
            "confidence": detection.confidence,
            "member_count": len(copied_files),
            "members": member_items,
        }

    def _create_loose_items_from_folder(
        self,
        session: Session,
        batch: Any,
        source_folder: Path,
        copied_files: list[tuple[Path, Path]],
        managed_source_id: int,
        target_root_id: int,
        operation_id: str,
    ) -> dict[str, Any]:
        """Create individual inbox items for each file (no object candidate)."""
        items: list[dict[str, Any]] = []
        for src_file, dest_file in copied_files:
            file_record = self._register_imported_file(
                session, src_file, dest_file, managed_source_id
            )
            classification = classify_file(
                dest_file.suffix.lstrip(".") if dest_file.suffix else None,
                str(dest_file),
            )
            inbox_item = self.repository.create_inbox_item(
                session,
                import_batch_id=batch.id,
                file_id=file_record.id,
                source_path=str(src_file),
                inbox_path=str(dest_file),
                status="imported",
                detected_file_kind=classification.file_kind,
                detected_placement=classification.auto_placement,
                target_library_root_id=target_root_id,
            )
            file_record.inbox_item_id = inbox_item.id
            items.append({
                "source_path": str(src_file),
                "inbox_path": str(dest_file),
                "file_id": file_record.id,
                "inbox_item_id": inbox_item.id,
            })
        session.flush()

        self.repository.append_journal_entry(
            session,
            operation_id=operation_id,
            operation_type="inbox_status_change",
            entity_type="import_batch",
            entity_id=batch.id,
            status="succeeded",
            after_json=json.dumps({"mode": "loose_files", "item_count": len(items)}),
        )

        return {"mode": "loose_files", "created_items": items}

    # ── object candidates ────────────────────────────────────

    def list_object_candidates(
        self, session: Session, *, page: int = 1, page_size: int = 50
    ):
        return self.repository.list_object_candidates(
            session, page=page, page_size=page_size
        )

    def get_object_candidate(self, session: Session, candidate_id: int):
        return self.repository.get_object_candidate(session, candidate_id)

    def get_object_candidate_with_members(
        self, session: Session, candidate_id: int
    ) -> dict[str, Any] | None:
        candidate = self.repository.get_object_candidate(session, candidate_id)
        if candidate is None:
            return None
        members = self.repository.list_object_members(session, candidate_id)
        member_details: list[dict[str, Any]] = []
        for m in members:
            inbox_item = self.repository.get_inbox_item(session, m.inbox_item_id)
            member_details.append({
                "id": m.id,
                "inbox_item_id": m.inbox_item_id,
                "role": m.role,
                "confidence": m.confidence,
                "reason": m.reason,
                "source_path": inbox_item.source_path if inbox_item else None,
                "inbox_path": inbox_item.inbox_path if inbox_item else None,
                "file_id": inbox_item.file_id if inbox_item else None,
            })
        return {
            "id": candidate.id,
            "import_batch_id": candidate.import_batch_id,
            "source_root_path": candidate.source_root_path,
            "inbox_root_path": candidate.inbox_root_path,
            "suggested_object_type": candidate.suggested_object_type,
            "final_object_type": candidate.final_object_type,
            "confidence": candidate.confidence,
            "status": candidate.status,
            "launch_file_id": candidate.launch_file_id,
            "primary_file_id": candidate.primary_file_id,
            "member_count": candidate.member_count,
            "reason_json": candidate.reason_json,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            "members": member_details,
        }

    # ── inbox item review ──────────────────────────────────

    def confirm_inbox_item(
        self, session: Session, item_id: int, *,
        final_object_type: str, target_library_root_id: int | None = None,
    ):
        item = self.repository.get_inbox_item(session, item_id)
        if item is None:
            raise ValueError("Inbox item not found.")
        if item.status in {"organized", "rejected", "archived"}:
            raise ValueError(f"Cannot confirm inbox item with status '{item.status}'.")
        if not final_object_type:
            raise ValueError("final_object_type is required.")
        if target_library_root_id is not None:
            root = self.root_repo.get_by_id(session, target_library_root_id)
            if root is None or not root.is_enabled:
                raise ValueError("Target library root not found or disabled.")
        item.final_object_type = final_object_type
        item.target_library_root_id = target_library_root_id
        item.status = "classified"
        item.updated_at = datetime.utcnow()
        session.flush()
        return item

    def reject_inbox_item(self, session: Session, item_id: int):
        item = self.repository.get_inbox_item(session, item_id)
        if item is None:
            raise ValueError("Inbox item not found.")
        if item.status in {"organized", "rejected", "archived"}:
            raise ValueError(f"Cannot reject inbox item with status '{item.status}'.")
        self.repository.update_inbox_item_status(session, item, "rejected")
        return item

    def create_candidate_from_inbox_item(
        self, session: Session, item_id: int,
    ):
        item = self.repository.get_inbox_item(session, item_id)
        if item is None:
            raise ValueError("Inbox item not found.")
        if item.organize_candidate_id is not None:
            raise ValueError("OrganizeCandidate already exists for this inbox item.")
        if item.status not in {"classified", "imported", "pending_review"}:
            raise ValueError(
                f"Cannot create candidate from inbox item with status '{item.status}'. "
                "Confirm classification first."
            )
        if not item.final_object_type:
            raise ValueError("final_object_type must be confirmed before creating candidate.")

        # check target root
        if item.target_library_root_id is None:
            raise ValueError("Target library root must be selected before creating candidate.")
        root = self.root_repo.get_by_id(session, item.target_library_root_id)
        if root is None or not root.is_enabled:
            raise ValueError("Target library root not found or disabled.")

        # verify inbox file still exists
        inbox_path = Path(item.inbox_path)
        if not inbox_path.exists():
            raise ValueError(f"Inbox file no longer exists: {item.inbox_path}")

        from app.db.models.organize import OrganizeCandidate
        now = datetime.utcnow()
        candidate = OrganizeCandidate(
            candidate_type="inbox_item",
            source_kind="file",  # "file" so organize creates mkdir+move+write_asset_yaml actions
            source_file_id=item.file_id,
            source_path=item.inbox_path,
            display_name=inbox_path.name,
            detected_type=item.final_object_type,
            confidence="high",
            reason=f"User-confirmed from inbox item #{item.id}",
            status="pending",
            created_at=now,
            updated_at=now,
        )
        session.add(candidate)
        session.flush()

        # link both ways
        item.organize_candidate_id = candidate.id
        session.flush()

        self.repository.append_journal_entry(
            session,
            operation_id=str(uuid.uuid4()),
            operation_type="inbox_status_change",
            entity_type="inbox_item",
            entity_id=item.id,
            status="succeeded",
            before_json=json.dumps({"status": item.status}),
            after_json=json.dumps({"organize_candidate_id": candidate.id}),
        )
        return candidate

    # ── object candidate review ─────────────────────────────

    def confirm_object_candidate(
        self, session: Session, oc_id: int, *,
        final_object_type: str,
        launch_file_id: int | None = None,
        target_library_root_id: int | None = None,
    ):
        oc = self.repository.get_object_candidate(session, oc_id)
        if oc is None:
            raise ValueError("Object candidate not found.")
        if oc.status in {"organized", "rejected"}:
            raise ValueError(f"Cannot confirm object candidate with status '{oc.status}'.")
        if not final_object_type:
            raise ValueError("final_object_type is required.")
        if target_library_root_id is not None:
            root = self.root_repo.get_by_id(session, target_library_root_id)
            if root is None or not root.is_enabled:
                raise ValueError("Target library root not found or disabled.")
        if launch_file_id is not None:
            members = self.repository.list_object_members(session, oc_id)
            member_file_ids = {
                self.repository.get_inbox_item(session, m.inbox_item_id).file_id
                for m in members
                if self.repository.get_inbox_item(session, m.inbox_item_id)
            }
            if launch_file_id not in member_file_ids:
                raise ValueError("launch_file_id must belong to a member of this object candidate.")
        oc.final_object_type = final_object_type
        oc.launch_file_id = launch_file_id or oc.launch_file_id
        oc.target_library_root_id = target_library_root_id
        oc.status = "confirmed"
        oc.updated_at = datetime.utcnow()
        session.flush()
        return oc

    def reject_object_candidate(self, session: Session, oc_id: int):
        oc = self.repository.get_object_candidate(session, oc_id)
        if oc is None:
            raise ValueError("Object candidate not found.")
        if oc.status in {"organized", "rejected"}:
            raise ValueError(f"Cannot reject object candidate with status '{oc.status}'.")
        oc.status = "rejected"
        oc.updated_at = datetime.utcnow()
        # reject member inbox items too
        members = self.repository.list_object_members(session, oc_id)
        for m in members:
            item = self.repository.get_inbox_item(session, m.inbox_item_id)
            if item and item.status not in {"organized", "rejected", "archived"}:
                self.repository.update_inbox_item_status(session, item, "rejected")
        session.flush()
        return oc

    def create_candidate_from_object_candidate(
        self, session: Session, oc_id: int,
    ):
        oc = self.repository.get_object_candidate(session, oc_id)
        if oc is None:
            raise ValueError("Object candidate not found.")
        if oc.organize_candidate_id is not None:
            raise ValueError("OrganizeCandidate already exists for this object candidate.")
        if oc.status != "confirmed":
            raise ValueError("Object candidate must be confirmed before creating organize candidate.")
        if not oc.final_object_type:
            raise ValueError("final_object_type must be confirmed first.")
        if oc.target_library_root_id is None:
            raise ValueError("Target library root must be selected first.")

        from app.db.models.organize import OrganizeCandidate
        now = datetime.utcnow()
        reason_data = {
            "import_object_candidate_id": oc.id,
            "suggested_object_type": oc.suggested_object_type,
            "inbox_root_path": oc.inbox_root_path,
            "member_count": oc.member_count,
        }
        if oc.launch_file_id:
            reason_data["launch_file_id"] = oc.launch_file_id
        # Use source_kind="file" so organize creates mkdir+move+write_asset_yaml
        # The move action moves the entire object root directory
        candidate = OrganizeCandidate(
            candidate_type="inbox_object",
            source_kind="file",
            source_path=oc.inbox_root_path,
            source_file_id=oc.primary_file_id or oc.launch_file_id,
            display_name=Path(oc.inbox_root_path).name,
            detected_type=oc.final_object_type,
            confidence=oc.confidence or "high",
            reason=json.dumps(reason_data),
            status="pending",
            created_at=now,
            updated_at=now,
        )
        session.add(candidate)
        session.flush()

        oc.organize_candidate_id = candidate.id
        session.flush()

        self.repository.append_journal_entry(
            session,
            operation_id=str(uuid.uuid4()),
            operation_type="inbox_status_change",
            entity_type="import_object_candidate",
            entity_id=oc.id,
            status="succeeded",
            after_json=json.dumps({"organize_candidate_id": candidate.id}),
        )
        return candidate

    # ── generate draft plan ─────────────────────────────────

    def generate_draft_plan_from_candidates(
        self, session: Session, candidate_ids: list[int],
    ):
        """Generate a draft OrganizePlan from OrganizeCandidate IDs.
        Does NOT mark ready, preflight, or execute."""
        from app.repositories.library_organize.repository import LibraryOrganizeRepository
        from app.services.library.organize import LibraryOrganizeService

        org_repo = LibraryOrganizeRepository()
        org_service = LibraryOrganizeService()

        # validate all candidates exist and are pending
        for cid in candidate_ids:
            c = org_repo.get_candidate(session, cid)
            if c is None:
                raise ValueError(f"OrganizeCandidate not found: {cid}")
            if c.status != "pending":
                raise ValueError(f"OrganizeCandidate {cid} is not pending (status: {c.status}).")

        # resolve target root from inbox item linked to first candidate
        from app.db.models.importing import InboxItem as InboxItemModel
        target_root_id = None
        inbox_item = session.query(InboxItemModel).filter(
            InboxItemModel.organize_candidate_id == candidate_ids[0]
        ).first()
        if inbox_item and inbox_item.target_library_root_id:
            target_root_id = inbox_item.target_library_root_id

        # generate draft plan (OrganizeService.generate_plan commits internally)
        result = org_service.generate_plan(
            session,
            candidate_ids=candidate_ids,
            target_library_root_id=target_root_id,
        )
        plan_id = result.plan_id

        # update inbox_item statuses to planned
        inbox_items = session.query(InboxItemModel).filter(
            InboxItemModel.organize_candidate_id.in_(candidate_ids)
        ).all()
        for item in inbox_items:
            self.repository.update_inbox_item_status(session, item, "planned")

        # update import_object_candidate statuses
        from app.db.models.importing import ImportObjectCandidate as IOCModel
        obj_candidates = session.query(IOCModel).filter(
            IOCModel.organize_candidate_id.in_(candidate_ids)
        ).all()
        for oc in obj_candidates:
            oc.status = "planned"
            oc.organize_plan_id = plan_id
            oc.updated_at = datetime.utcnow()
            # sync member inbox item statuses
            members = self.repository.list_object_members(session, oc.id)
            for m in members:
                item = self.repository.get_inbox_item(session, m.inbox_item_id)
                if item and item.status not in {"organized", "rejected", "archived"}:
                    self.repository.update_inbox_item_status(session, item, "planned")

        # populate action FKs for v2 traceability
        from app.db.models.organize import OrganizeAction
        from app.db.models.importing import ImportObjectCandidate as IOCModel

        # collect inbox_item_ids and object_candidate_ids per organize_candidate
        candidate_inbox_map: dict[int, int] = {}
        candidate_object_map: dict[int, int] = {}
        for cid in candidate_ids:
            ii = session.query(InboxItemModel).filter(
                InboxItemModel.organize_candidate_id == cid
            ).first()
            if ii:
                candidate_inbox_map[cid] = ii.id
            oc = session.query(IOCModel).filter(
                IOCModel.organize_candidate_id == cid
            ).first()
            if oc:
                candidate_object_map[cid] = oc.id

        # set FKs on plan actions
        if candidate_inbox_map or candidate_object_map:
            actions = session.query(OrganizeAction).filter(
                OrganizeAction.plan_id == plan_id
            ).all()
            for action in actions:
                # use first available mapping (single-candidate plan typical for v2)
                if candidate_inbox_map:
                    action.inbox_item_id = next(iter(candidate_inbox_map.values()))
                if candidate_object_map:
                    action.import_object_candidate_id = next(iter(candidate_object_map.values()))

        session.flush()

        # get plan for response
        plan = org_repo.get_plan(session, plan_id)
        return plan

    # ── internal helpers ────────────────────────────────────

    def _resolve_inbox_root(self, session: Session):
        root = self.root_repo.get_default(session)
        if root is None:
            raise ValueError(
                "No enabled managed library root. Please configure one in Library > Roots."
            )
        resolved = Path(root.root_path).resolve()
        if not resolved.exists():
            raise ValueError(f"Managed library root does not exist on disk: {root.root_path}")
        return root

    def _get_managed_source(self, session: Session):
        source = session.query(Source).filter(
            Source.path == "__workbench_managed_import__"
        ).one_or_none()
        if source is None:
            now = datetime.utcnow()
            source = Source(
                path="__workbench_managed_import__",
                display_name="Managed Import",
                is_enabled=True,
                scan_mode="manual",
                last_scan_status="not_applicable",
                created_at=now,
                updated_at=now,
            )
            session.add(source)
            session.flush()
        return source

    def _ensure_inbox_dir(self, root_path: str, batch_id: int) -> Path:
        inbox_dir = Path(root_path) / "00_Inbox" / str(batch_id)
        inbox_dir.mkdir(parents=True, exist_ok=True)
        return inbox_dir

    def _copy_one_file(
        self,
        session: Session,
        batch: Any,
        source_path_str: str,
        inbox_dir: Path,
        managed_source_id: int,
        target_root_id: int,
        operation_id: str,
    ) -> ImportFileResult:
        source = Path(source_path_str).resolve()
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source_path_str}")
        if not source.is_file():
            raise ValueError(f"Source path is not a file: {source_path_str}")

        # compute no-overwrite target
        target = self._no_overwrite_target(inbox_dir / source.name)

        # journal: copy started
        self.repository.append_journal_entry(
            session,
            operation_id=operation_id,
            operation_type="import_copy",
            entity_type="inbox_item",
            status="started",
            before_json=json.dumps({"source_path": str(source)}),
            after_json=json.dumps({"target_path": str(target)}),
        )

        # copy to temp then rename (atomic-ish)
        tmp_target = target.with_name(f".tmp-{uuid.uuid4().hex[:8]}-{target.name}")
        try:
            shutil.copy2(str(source), str(tmp_target))
            tmp_target.replace(target)
        except Exception:
            if tmp_target.exists():
                tmp_target.unlink(missing_ok=True)
            self.repository.append_journal_entry(
                session,
                operation_id=operation_id,
                operation_type="import_copy",
                entity_type="inbox_item",
                status="failed",
                error_message="File copy failed",
            )
            raise

        # journal: copy succeeded
        self.repository.append_journal_entry(
            session,
            operation_id=operation_id,
            operation_type="import_copy",
            entity_type="inbox_item",
            status="succeeded",
        )

        # register file in files table
        file_record = self._register_imported_file(
            session, source, target, managed_source_id
        )

        # journal: file record created
        self.repository.append_journal_entry(
            session,
            operation_id=operation_id,
            operation_type="file_record_create",
            entity_type="file",
            entity_id=file_record.id,
            status="succeeded",
        )

        # create inbox item
        classification = classify_file(
            target.suffix.lstrip(".") if target.suffix else None,
            str(target),
        )
        detected_object_type = self._detect_object_type(classification.file_kind)

        inbox_item = self.repository.create_inbox_item(
            session,
            import_batch_id=batch.id,
            file_id=file_record.id,
            source_path=str(source),
            inbox_path=str(target),
            status="imported",
            detected_file_kind=classification.file_kind,
            detected_placement=classification.auto_placement,
            detected_object_type=detected_object_type,
            target_library_root_id=target_root_id,
        )

        # link file to inbox item
        file_record.inbox_item_id = inbox_item.id
        session.flush()

        # journal: inbox item created
        self.repository.append_journal_entry(
            session,
            operation_id=operation_id,
            operation_type="inbox_status_change",
            entity_type="inbox_item",
            entity_id=inbox_item.id,
            status="succeeded",
            before_json=json.dumps({"status": "imported"}),
        )

        return ImportFileResult(
            source_path=str(source),
            inbox_path=str(target),
            file_id=file_record.id,
            inbox_item_id=inbox_item.id,
            status="ok",
        )

    # ── Phase 7H-3: Multi-file Collection Import ──────────────

    @staticmethod
    def suggest_collection_name(paths: list[str]) -> str:
        """Generate a collection name from selected file basenames."""
        import re as _re
        from datetime import datetime as _dt

        if not paths:
            return "Collection"

        # strip extensions and normalize separators
        stems: list[str] = []
        for p in paths:
            s = PurePath(p).stem
            s = _re.sub(r"[_\-.\s]+", " ", s).strip()
            if s:
                stems.append(s)

        if not stems:
            return f"Collection {_dt.now().strftime('%Y-%m-%d %H%M')}"

        # find longest common prefix
        prefix = stems[0]
        for s in stems[1:]:
            while prefix and not s.lower().startswith(prefix.lower()):
                prefix = prefix[:-1].rstrip()

        prefix = prefix.strip()

        # trim trailing sequence tokens
        prefix = _re.sub(
            r"\s*(S?\d{1,2}[Ee]\d{1,3}|EP?\d{2,3}|Lesson\s*\d{2,3}|Part\s*\d{2,3}|Chapter\s*\d{2,3}|第?\d{2,3}[课章节]?|\d{2,4})\s*$",
            "", prefix,
        ).strip()
        # second pass: trim any remaining trailing digits (handles partial numeric common prefixes)
        prefix = _re.sub(r"\s+\d*\s*$", "", prefix).strip()

        # reject if too short, too generic, or empty
        GENERIC_PREFIXES = {"img", "dsc", "vid", "dscn", "pict", "mov", "clip", "img_", "dsc_"}
        if len(prefix) < 3 or prefix.lower() in GENERIC_PREFIXES or not prefix:
            prefix = f"Collection {_dt.now().strftime('%Y-%m-%d %H%M')}"

        # Windows-safe sanitize
        prefix = _re.sub(r'[\\/:*?"<>|]', " ", prefix)
        prefix = _re.sub(r"\s+", " ", prefix).strip()
        prefix = prefix.rstrip(". ")

        return prefix or f"Collection {_dt.now().strftime('%Y-%m-%d %H%M')}"

    @staticmethod
    def suggest_type_for_files(paths: list[str]) -> tuple[str | None, str]:
        """Suggest object type for a set of selected files. Returns (type, confidence)."""
        exts: set[str] = set()
        for p in paths:
            ext = PurePath(p).suffix.lower().lstrip(".")
            if ext:
                exts.add(ext)

        video_exts = {"mp4", "mkv", "avi", "mov", "webm", "wmv", "m4v", "mpg", "mpeg"}
        image_exts = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "tif"}
        audio_exts = {"mp3", "wav", "flac", "ogg", "m4a", "aac", "opus"}
        doc_exts = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "md", "rtf"}

        video_count = sum(1 for e in exts if e in video_exts)
        image_count = sum(1 for e in exts if e in image_exts)
        audio_count = sum(1 for e in exts if e in audio_exts)
        doc_count = sum(1 for e in exts if e in doc_exts)

        total = len(exts) or 1

        if video_count > 0 and image_count + audio_count + doc_count == 0:
            return "video_collection", "medium"
        if video_count > 0 and doc_count > 0:
            return "course", "medium"
        if image_count > 0 and video_count + audio_count == 0:
            return "imgset", "medium"
        if audio_count > 0 and video_count + image_count == 0:
            return "audio", "medium"
        if video_count + image_count + audio_count + doc_count >= 3:
            return "asset_pack", "low"
        return None, "unknown"

    def import_file_collection(
        self,
        session: Session,
        *,
        paths: list[str],
        collection_name: str,
        suggested_object_type: str | None = None,
        target_library_root_id: int | None = None,
    ) -> dict[str, Any]:
        """Phase 7H-3: Import selected files as a synthetic collection object."""
        import re as _re

        # validate paths
        if not paths:
            raise ValueError("At least one file path is required.")
        for p in paths:
            sp = Path(p).resolve()
            if not sp.is_file():
                raise ValueError(f"Path is not an existing file: {p}")

        # sanitize collection name
        collection_name = _re.sub(r'[\\/:*?"<>|]', " ", collection_name)
        collection_name = _re.sub(r"\s+", " ", collection_name).strip()
        collection_name = collection_name.rstrip(". ")
        if not collection_name:
            raise ValueError("Collection name is required.")

        # validate target root
        if target_library_root_id is not None:
            lib_root = self.root_repo.get_by_id(session, target_library_root_id)
            if lib_root is None:
                raise ValueError("Target library root not found.")
            if not lib_root.is_enabled:
                raise ValueError("Target library root is disabled.")

        # create batch
        batch = self.repository.create_batch(
            session, source_kind="file_collection", import_method="copy"
        )
        self.repository.update_batch_status(session, batch, "running")

        op_id = str(uuid.uuid4())
        target_root = self._resolve_inbox_root(session)
        managed_source = self._get_managed_source(session)

        # create synthetic inbox folder
        inbox_parent = self._ensure_inbox_dir(target_root.root_path, batch.id)
        synthetic_folder = self._no_overwrite_target(inbox_parent / collection_name)

        self.repository.append_journal_entry(
            session,
            operation_id=op_id,
            operation_type="import_collection_copy",
            entity_type="import_batch",
            entity_id=batch.id,
            status="started",
            before_json=json.dumps({"source_paths": [str(Path(p).resolve()) for p in paths]}),
            after_json=json.dumps({"synthetic_folder": str(synthetic_folder)}),
        )

        synthetic_folder.mkdir(parents=True, exist_ok=True)

        # copy files into synthetic folder
        copied: list[tuple[Path, Path, File]] = []  # (source, dest, file_record)
        failed: list[dict[str, Any]] = []
        for p in paths:
            source_path = Path(p).resolve()
            target_file = self._no_overwrite_target(synthetic_folder / source_path.name)
            tmp = target_file.with_name(f".tmp-{uuid.uuid4().hex[:8]}-{target_file.name}")
            try:
                shutil.copy2(str(source_path), str(tmp))
                tmp.replace(target_file)
                file_record = self._register_imported_file(
                    session, source_path, target_file, managed_source.id
                )
                copied.append((source_path, target_file, file_record))
            except Exception as exc:
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
                failed.append({"path": str(source_path), "error": str(exc)})

        # collect relative member paths for detection
        member_rel_paths = [str(dest.relative_to(synthetic_folder)) for _src, dest, _fr in copied]

        # detect object type from folder + member paths
        detection = detect_object_type(collection_name, member_rel_paths)

        # override suggestion with user-provided if given
        final_suggested = suggested_object_type or detection.suggested_object_type or "unknown"

        # create object candidate
        reason_json = json.dumps({
            "signals": detection.signals,
            "member_count": len(copied),
        })
        obj_candidate = self.repository.create_object_candidate(
            session,
            import_batch_id=batch.id,
            source_root_path=str(copied[0][0].parent) if copied else "",
            inbox_root_path=str(synthetic_folder),
            suggested_object_type=final_suggested,
            confidence=detection.confidence,
            member_count=len(copied),
            reason_json=reason_json,
        )
        obj_candidate.status = "pending_review"

        # create inbox_items and object_members
        member_items: list[dict[str, Any]] = []
        for src_file, dest_file, file_record in copied:
            rel_path = str(dest_file.relative_to(synthetic_folder))
            classification = classify_file(
                dest_file.suffix.lstrip(".") if dest_file.suffix else None,
                str(dest_file),
            )
            inbox_item = self.repository.create_inbox_item(
                session,
                import_batch_id=batch.id,
                file_id=file_record.id,
                source_path=str(src_file),
                inbox_path=str(dest_file),
                status="imported",
                detected_file_kind=classification.file_kind,
                detected_placement=classification.auto_placement,
                target_library_root_id=target_library_root_id,
            )
            file_record.inbox_item_id = inbox_item.id

            role_info = detection.member_roles.get(rel_path)
            role = role_info.role if role_info else "unknown_child"
            role_confidence = role_info.confidence if role_info else "low"
            role_reason = role_info.reason if role_info else "Member of collection import"

            self.repository.create_object_member(
                session,
                import_object_candidate_id=obj_candidate.id,
                inbox_item_id=inbox_item.id,
                role=role,
                confidence=role_confidence,
                reason=role_reason,
            )
            member_items.append({
                "relative_path": rel_path,
                "file_id": file_record.id,
                "inbox_item_id": inbox_item.id,
                "role": role,
            })

        # set launch/cover file references
        if detection.launch_candidate_path:
            for item in member_items:
                if item["relative_path"] == detection.launch_candidate_path:
                    obj_candidate.launch_file_id = item["file_id"]
                    break
        if detection.cover_candidate_path:
            for item in member_items:
                if item["relative_path"] == detection.cover_candidate_path:
                    obj_candidate.primary_file_id = item["file_id"]
                    break

        session.flush()

        # finalize batch
        total = len(copied) + len(failed)
        self.repository.update_batch_counts(
            session, batch,
            file_count=total, completed_count=len(copied), failed_count=len(failed),
        )
        final_status = "completed" if not failed else "completed_with_errors"
        self.repository.update_batch_status(session, batch, final_status)

        self.repository.append_journal_entry(
            session,
            operation_id=op_id,
            operation_type="import_collection_copy",
            entity_type="import_batch",
            entity_id=batch.id,
            status="succeeded" if not failed else "completed_with_errors",
            after_json=json.dumps({
                "copied": len(copied), "failed": len(failed),
                "synthetic_folder": str(synthetic_folder),
                "object_candidate_id": obj_candidate.id,
            }),
        )

        session.commit()

        return {
            "batch_id": batch.id,
            "object_candidate_id": obj_candidate.id,
            "suggested_object_type": final_suggested,
            "confidence": detection.confidence,
            "member_count": len(member_items),
            "members": member_items,
            "failed_items": failed,
        }

    @staticmethod
    def _no_overwrite_target(target: Path) -> Path:
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        parent = target.parent
        counter = 1
        while True:
            candidate = parent / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    @staticmethod
    def _register_imported_file(
        session: Session,
        source: Path,
        target: Path,
        managed_source_id: int,
    ) -> File:
        classification = classify_file(
            target.suffix.lstrip(".") if target.suffix else None,
            str(target),
        )
        stat = target.stat()
        now = datetime.utcnow()
        file = File(
            source_id=managed_source_id,
            path=str(target),
            parent_path=str(target.parent),
            name=target.name,
            stem=target.stem,
            extension=target.suffix.lstrip(".") if target.suffix else None,
            file_type=_FILE_KIND_TO_TYPE.get(classification.file_kind, "other"),
            file_kind=classification.file_kind,
            auto_placement=classification.auto_placement,
            storage_state="inbox",
            original_path=str(source),
            mime_type=None,
            size_bytes=stat.st_size,
            created_at_fs=datetime.fromtimestamp(stat.st_ctime),
            modified_at_fs=datetime.fromtimestamp(stat.st_mtime),
            discovered_at=now,
            last_seen_at=now,
            is_deleted=False,
            checksum_hint=None,
            updated_at=now,
        )
        session.add(file)
        session.flush()
        return file

    @staticmethod
    def _detect_object_type(file_kind: str) -> str | None:
        kind_to_type: dict[str, str] = {
            "video": "clip",
            "image": "imgset",
            "audio": "audio",
            "document": "docset",
            "ebook": "docset",
            "archive": "",
            "executable": "software",
            "installer": "software",
        }
        return kind_to_type.get(file_kind)

    # ── Phase 8C-1: Compose inbox loose items ────────────────

    def compose_inbox_items(
        self,
        session: Session,
        *,
        inbox_item_ids: list[int],
        object_name: str,
        suggested_object_type: str | None = None,
        target_library_root_id: int | None = None,
    ) -> dict[str, Any]:
        """Compose multiple inbox loose items into one import_object_candidate.

        No filesystem operations. This is a pure DB grouping — the inbox items
        already exist in staging. The new object candidate logically groups them.

        Requirements:
        - All items must be from the same import_batch
        - Items must be in imported/pending_review/classified status (not organized/rejected)
        - Items must not already be members of another active object candidate
        """
        import re as _re

        if not inbox_item_ids:
            raise ValueError("At least one inbox item is required.")

        # Validate target root
        if target_library_root_id is not None:
            lib_root = self.root_repo.get_by_id(session, target_library_root_id)
            if lib_root is None or not lib_root.is_enabled:
                raise ValueError("Target library root not found or disabled.")

        # Sanitize object name
        object_name = _re.sub(r'[\\/:*?"<>|]', " ", object_name)
        object_name = _re.sub(r"\s+", " ", object_name).strip()
        if not object_name:
            raise ValueError("Object name is required.")

        # Load and validate all items
        items: list[Any] = []
        first_batch_id: int | None = None
        UNCOMPOSABLE_STATUSES = {"organized", "rejected", "archived", "failed"}

        for iid in inbox_item_ids:
            item = self.repository.get_inbox_item(session, iid)
            if item is None:
                raise ValueError(f"Inbox item not found: {iid}")

            # Same batch
            if first_batch_id is None:
                first_batch_id = item.import_batch_id
            elif item.import_batch_id != first_batch_id:
                raise ValueError(
                    f"Compose from multiple import batches is not supported in Phase 8C-1. "
                    f"Item {iid} is in batch {item.import_batch_id}, expected {first_batch_id}."
                )

            # Uncomposable status
            if item.status in UNCOMPOSABLE_STATUSES:
                raise ValueError(
                    f"Inbox item {iid} has status '{item.status}' and cannot be composed."
                )

            # Not already a member
            from app.db.models.importing import ImportObjectCandidate as IOC, ImportObjectMember as IOM
            existing_member = session.query(IOM).filter(
                IOM.inbox_item_id == iid
            ).join(IOC, IOM.import_object_candidate_id == IOC.id).filter(
                IOC.status.in_(["pending_review", "confirmed"])
            ).first()
            if existing_member is not None:
                raise ValueError(
                    f"Inbox item {iid} is already a member of object candidate "
                    f"{existing_member.import_object_candidate_id}"
                )
            items.append(item)

        # Transaction: create batch, candidate, members atomically
        op_id = str(uuid.uuid4())
        target_root = self._resolve_inbox_root(session)

        batch = self.repository.create_batch(
            session, source_kind="compose", import_method="copy"
        )
        self.repository.update_batch_status(session, batch, "running")

        self.repository.append_journal_entry(
            session, operation_id=op_id, operation_type="compose_object",
            entity_type="import_batch", entity_id=batch.id, status="started",
            before_json=json.dumps({"inbox_item_ids": inbox_item_ids}),
        )

        # Logical inbox root path — derived from existing items (no mkdir)
        existing_inbox_paths = [item.inbox_path for item in items if item.inbox_path]
        logical_root = str(Path(existing_inbox_paths[0]).parent / object_name) if existing_inbox_paths else object_name

        # Create object candidate (pending_review — requires user review)
        oc = self.repository.create_object_candidate(
            session,
            import_batch_id=batch.id,
            source_root_path="",
            inbox_root_path=logical_root,
            suggested_object_type=suggested_object_type or "unknown",
            confidence="low",
            member_count=len(items),
            reason_json=json.dumps({"source": "compose_inbox", "item_count": len(items)}),
        )
        oc.status = "pending_review"
        if target_library_root_id:
            oc.target_library_root_id = target_library_root_id

        try:
            # Collect member paths for type detection
            member_rel_paths: list[str] = []

            # Create members and update inbox items
            member_items: list[dict[str, Any]] = []
            for item in items:
                role = "unknown_child"
                if item.detected_file_kind:
                    kind = item.detected_file_kind
                    if kind in ("video",):
                        role = "main_video"
                    elif kind in ("image",):
                        role = "image_member"
                    elif kind in ("document", "ebook"):
                        role = "document_attachment"
                    elif kind in ("executable",):
                        role = "launch_exe"

                rel_path = Path(item.inbox_path).name if item.inbox_path else ""
                member_rel_paths.append(rel_path)

                if not oc.launch_file_id and role in ("launch_exe", "main_video", "support_exe"):
                    oc.launch_file_id = item.file_id
                if not oc.primary_file_id and role in ("image_member", "cover"):
                    oc.primary_file_id = item.file_id

                self.repository.create_object_member(
                    session,
                    import_object_candidate_id=oc.id,
                    inbox_item_id=item.id,
                    role=role,
                    confidence="low",
                    reason="Composed from inbox loose items",
                )

                # classified: grouped into object candidate, still pending user review
                item.status = "classified"
                item.detected_object_type = suggested_object_type or item.detected_object_type
                if target_library_root_id:
                    item.target_library_root_id = target_library_root_id
                item.updated_at = datetime.utcnow()

                member_items.append({
                    "inbox_item_id": item.id,
                    "file_id": item.file_id,
                    "role": role,
                })

            session.flush()

            # Try type detection from member paths
            from app.services.importing.object_boundary import detect_object_type
            detection = detect_object_type(object_name, member_rel_paths)
            if detection.suggested_object_type and detection.suggested_object_type != "unknown":
                if not suggested_object_type:
                    oc.suggested_object_type = detection.suggested_object_type
                    oc.confidence = detection.confidence

            # Finalize batch
            self.repository.update_batch_counts(
                session, batch,
                file_count=len(items), completed_count=len(items), failed_count=0,
            )
            self.repository.update_batch_status(session, batch, "completed")
            self.repository.append_journal_entry(
                session, operation_id=op_id, operation_type="compose_object",
                entity_type="import_batch", entity_id=batch.id, status="succeeded",
                after_json=json.dumps({"object_candidate_id": oc.id, "member_count": len(items)}),
            )
            session.commit()

            return {
                "object_candidate_id": oc.id,
                "import_batch_id": batch.id,
                "object_name": object_name,
                "suggested_object_type": oc.suggested_object_type,
                "confidence": oc.confidence or "low",
                "member_count": len(items),
                "members": member_items,
                "notes": [
                    "Object candidate created. Review required before draft plan.",
                    "No files were moved — only inbox references were linked.",
                    "classified means grouped into object candidate, still pending user review.",
                ],
            }

        except Exception:
            session.rollback()
            raise

    # ── Phase 8C-3: Compose external loose files ──────────────

    def compose_external_files(
        self,
        session: Session,
        *,
        file_ids: list[int],
        object_name: str,
        suggested_object_type: str | None = None,
        target_library_root_id: int | None = None,
    ) -> dict[str, Any]:
        """Copy external loose files into Inbox and compose into an object candidate.

        Source files are copy-only — never moved or deleted. Inbox copies are
        registered as new files (storage_state=inbox), then grouped into a
        pending_review import_object_candidate.
        """
        import re as _re
        from app.db.models.importing import ImportObjectCandidate as IOC, ImportObjectMember as IOM

        if not file_ids:
            raise ValueError("At least one file is required.")

        # Validate target root
        if target_library_root_id is not None:
            lib_root = self.root_repo.get_by_id(session, target_library_root_id)
            if lib_root is None or not lib_root.is_enabled:
                raise ValueError("Target library root not found or disabled.")

        # Sanitize object name
        object_name = _re.sub(r'[\\/:*?"<>|]', " ", object_name)
        object_name = _re.sub(r"\s+", " ", object_name).strip()
        if not object_name:
            raise ValueError("Object name is required.")

        # Load and validate all files
        files: list[File] = []
        member_file_ids: set[int] = set()

        # Gather existing member file_ids to reject already-composed files
        from app.db.models.library_object import LibraryObjectMember as LOM
        lom_ids = session.query(LOM.file_id).filter(
            LOM.file_id.isnot(None),
            LOM.member_status == "active",
        ).all()
        member_file_ids.update(r[0] for r in lom_ids if r[0] is not None)

        from app.db.models.importing import InboxItem as II
        iom_ii_ids = session.query(IOM.inbox_item_id).join(
            IOC, IOM.import_object_candidate_id == IOC.id
        ).filter(IOC.status.in_(["pending_review", "confirmed"])).all()
        ii_ids = [r[0] for r in iom_ii_ids if r[0] is not None]
        if ii_ids:
            ii_fids = session.query(II.file_id).filter(II.id.in_(ii_ids)).all()
            member_file_ids.update(r[0] for r in ii_fids if r[0] is not None)

        for fid in file_ids:
            f = session.query(File).filter(File.id == fid).first()
            if f is None:
                raise ValueError(f"File not found: {fid}")
            if f.storage_state != "external":
                raise ValueError(f"File {fid} must have storage_state=external, got {f.storage_state}")
            if f.is_deleted:
                raise ValueError(f"File {fid} is deleted.")
            source_path = Path(f.path)
            if not source_path.is_file():
                raise ValueError(f"Source file does not exist on disk: {f.path}")
            if fid in member_file_ids:
                raise ValueError(f"File {fid} is already a member of an object.")
            files.append(f)

        # Create batch and Inbox folder
        op_id = str(uuid.uuid4())
        batch = self.repository.create_batch(
            session, source_kind="compose_external", import_method="copy"
        )
        self.repository.update_batch_status(session, batch, "running")

        target_root = self._resolve_inbox_root(session)
        inbox_parent = self._ensure_inbox_dir(target_root.root_path, batch.id)
        inbox_folder = self._no_overwrite_target(inbox_parent / object_name)

        self.repository.append_journal_entry(
            session, operation_id=op_id, operation_type="compose_external",
            entity_type="import_batch", entity_id=batch.id, status="started",
            before_json=json.dumps({"source_file_ids": file_ids}),
            after_json=json.dumps({"inbox_folder": str(inbox_folder)}),
        )

        copied: list[tuple[Path, Path, File]] = []
        try:
            inbox_folder.mkdir(parents=True, exist_ok=True)
            for f in files:
                source_path = Path(f.path)
                dest = self._no_overwrite_target(inbox_folder / source_path.name)
                tmp = dest.with_name(f".tmp-{uuid.uuid4().hex[:8]}-{dest.name}")
                try:
                    shutil.copy2(str(source_path), str(tmp))
                    tmp.replace(dest)
                    file_rec = self._register_imported_file(
                        session, source_path, dest, self._get_managed_source(session).id
                    )
                    copied.append((source_path, dest, file_rec))
                except Exception:
                    if tmp.exists():
                        tmp.unlink(missing_ok=True)
                    raise
        except Exception:
            # Clean up created inbox folder on failure
            session.rollback()
            if inbox_folder.exists():
                shutil.rmtree(str(inbox_folder), ignore_errors=True)
            raise

        try:
            # Create members
            member_rel_paths: list[str] = []
            member_items: list[dict[str, Any]] = []

            for source_path, dest, file_rec in copied:
                rel_path = str(dest.relative_to(inbox_folder))
                member_rel_paths.append(rel_path)

                kind = file_rec.file_kind or "other"
                role = "unknown_child"
                if kind == "image":
                    role = "image_member"
                elif kind == "video":
                    role = "main_video"
                elif kind == "document":
                    role = "document_attachment"
                elif kind in ("executable",):
                    role = "launch_exe"

                ii = self.repository.create_inbox_item(
                    session,
                    import_batch_id=batch.id,
                    file_id=file_rec.id,
                    source_path=str(source_path),
                    inbox_path=str(dest),
                    status="imported",
                    detected_file_kind=kind,
                    detected_placement=file_rec.auto_placement,
                    target_library_root_id=target_library_root_id,
                )
                file_rec.inbox_item_id = ii.id

                member_items.append({
                    "file_id": file_rec.id,
                    "inbox_item_id": ii.id,
                    "source_file_id": Path(str(source_path)).name,
                    "name": file_rec.name,
                    "role": role,
                })

            session.flush()

            # Create object candidate
            oc = self.repository.create_object_candidate(
                session,
                import_batch_id=batch.id,
                source_root_path=str(Path(files[0].path).parent) if files else "",
                inbox_root_path=str(inbox_folder),
                suggested_object_type=suggested_object_type or "unknown",
                confidence="low",
                member_count=len(copied),
                reason_json=json.dumps({
                    "source": "compose_external",
                    "original_file_ids": file_ids,
                    "copy_only": True,
                    "source_preserved": True,
                }),
            )
            oc.status = "pending_review"

            for mi in member_items:
                ii_id = mi["inbox_item_id"]
                role = mi["role"]
                self.repository.create_object_member(
                    session,
                    import_object_candidate_id=oc.id,
                    inbox_item_id=ii_id,
                    role=role,
                    confidence="low",
                    reason="Composed from external loose file",
                )

            if target_library_root_id:
                oc.target_library_root_id = target_library_root_id

            # Type detection
            from app.services.importing.object_boundary import detect_object_type
            detection = detect_object_type(object_name, member_rel_paths)
            if detection.suggested_object_type and detection.suggested_object_type != "unknown":
                if not suggested_object_type:
                    oc.suggested_object_type = detection.suggested_object_type
                    oc.confidence = detection.confidence

            session.flush()

            self.repository.update_batch_counts(
                session, batch,
                file_count=len(copied), completed_count=len(copied), failed_count=0,
            )
            self.repository.update_batch_status(session, batch, "completed")
            self.repository.append_journal_entry(
                session, operation_id=op_id, operation_type="compose_external",
                entity_type="import_batch", entity_id=batch.id, status="succeeded",
                after_json=json.dumps({
                    "object_candidate_id": oc.id,
                    "copied_count": len(copied),
                    "source_preserved": True,
                }),
            )
            session.commit()

            return {
                "import_batch_id": batch.id,
                "object_candidate_id": oc.id,
                "object_name": object_name,
                "suggested_object_type": oc.suggested_object_type,
                "confidence": oc.confidence or "low",
                "member_count": len(member_items),
                "copied_count": len(copied),
                "status": oc.status,
                "members": member_items,
                "notes": [
                    "External source files were copied to Inbox. Source files were not moved or deleted.",
                    "Object candidate created as pending_review. Review required before draft plan.",
                    "No organize candidate, draft plan, or execute was triggered.",
                ],
            }

        except Exception:
            session.rollback()
            # Clean up created inbox folder
            if inbox_folder.exists():
                shutil.rmtree(str(inbox_folder), ignore_errors=True)
            raise


import_service = ImportService()
