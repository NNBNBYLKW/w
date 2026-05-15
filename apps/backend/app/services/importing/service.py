from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
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
            raise ValueError("Managed import source not initialized.")
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
            "image": "image",
            "audio": "audio",
            "document": "document",
            "ebook": "document",
            "archive": "archive",
            "executable": "software",
            "installer": "software",
        }
        return kind_to_type.get(file_kind)


import_service = ImportService()
