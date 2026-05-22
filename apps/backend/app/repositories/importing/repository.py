from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.time import utcnow

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.importing import (
    FilePathHistory,
    ImportBatch,
    ImportObjectCandidate,
    ImportObjectMember,
    InboxItem,
    OperationJournal,
)


@dataclass(frozen=True)
class InboxItemFilters:
    page: int
    page_size: int
    status: str | None = None
    batch_id: int | None = None


class ImportRepository:
    # ——— ImportBatch ————————————————————————————————————————

    def create_batch(
        self, session: Session, *, source_kind: str, import_method: str = "copy"
    ) -> ImportBatch:
        batch = ImportBatch(
            source_kind=source_kind,
            import_method=import_method,
            created_at=utcnow(),
        )
        session.add(batch)
        session.flush()
        return batch

    def get_batch(self, session: Session, batch_id: int) -> ImportBatch | None:
        return session.get(ImportBatch, batch_id)

    def list_batches(
        self, session: Session, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[ImportBatch], int]:
        base = select(ImportBatch)
        total = session.scalar(select(func.count()).select_from(base.subquery()))
        offset = (page - 1) * page_size
        items = list(
            session.scalars(
                base.order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        return items, total or 0

    def update_batch_counts(
        self,
        session: Session,
        batch: ImportBatch,
        *,
        completed_count: int | None = None,
        failed_count: int | None = None,
        file_count: int | None = None,
    ) -> ImportBatch:
        if completed_count is not None:
            batch.completed_count = completed_count
        if failed_count is not None:
            batch.failed_count = failed_count
        if file_count is not None:
            batch.file_count = file_count
        session.flush()
        return batch

    def update_batch_status(
        self, session: Session, batch: ImportBatch, status: str, *, error_summary: str | None = None
    ) -> ImportBatch:
        batch.status = status
        if error_summary is not None:
            batch.error_summary = error_summary
        if status in {"completed", "completed_with_errors", "failed", "cancelled"}:
            batch.finished_at = utcnow()
        session.flush()
        return batch

    # ——— InboxItem ——————————————————————————————————————————

    def create_inbox_item(
        self,
        session: Session,
        *,
        import_batch_id: int,
        source_path: str,
        inbox_path: str,
        file_id: int | None = None,
        status: str = "imported",
        detected_file_kind: str | None = None,
        detected_placement: str | None = None,
        detected_object_type: str | None = None,
        target_library_root_id: int | None = None,
    ) -> InboxItem:
        now = utcnow()
        item = InboxItem(
            import_batch_id=import_batch_id,
            file_id=file_id,
            source_path=source_path,
            inbox_path=inbox_path,
            status=status,
            detected_file_kind=detected_file_kind,
            detected_placement=detected_placement,
            detected_object_type=detected_object_type,
            target_library_root_id=target_library_root_id,
            created_at=now,
            updated_at=now,
        )
        session.add(item)
        session.flush()
        return item

    def get_inbox_item(self, session: Session, item_id: int) -> InboxItem | None:
        return session.get(InboxItem, item_id)

    def list_inbox_items(
        self, session: Session, *, filters: InboxItemFilters | None = None
    ) -> tuple[list[InboxItem], int]:
        page = 1 if filters is None else filters.page
        page_size = 50 if filters is None else filters.page_size

        stmts = []
        if filters is not None:
            if filters.status is not None:
                stmts.append(InboxItem.status == filters.status)
            if filters.batch_id is not None:
                stmts.append(InboxItem.import_batch_id == filters.batch_id)

        base = select(InboxItem).where(*stmts) if stmts else select(InboxItem)
        total = session.scalar(select(func.count()).select_from(base.subquery()))
        offset = (page - 1) * page_size
        items = list(
            session.scalars(
                base.order_by(InboxItem.created_at.desc(), InboxItem.id.desc())
                .offset(offset)
                .limit(page_size)
            )
        )
        return items, total or 0

    def update_inbox_item_status(
        self, session: Session, item: InboxItem, status: str, *, error_message: str | None = None
    ) -> InboxItem:
        item.status = status
        if error_message is not None:
            item.error_message = error_message
        item.updated_at = utcnow()
        session.flush()
        return item

    def update_inbox_item(
        self,
        session: Session,
        item: InboxItem,
        *,
        final_object_type: str | None = None,
        target_library_root_id: int | None = None,
        organize_candidate_id: int | None = None,
    ) -> InboxItem:
        if final_object_type is not None:
            item.final_object_type = final_object_type
        if target_library_root_id is not None:
            item.target_library_root_id = target_library_root_id
        if organize_candidate_id is not None:
            item.organize_candidate_id = organize_candidate_id
        item.updated_at = utcnow()
        session.flush()
        return item

    # ——— OperationJournal ————————————————————————————————————

    def append_journal_entry(
        self,
        session: Session,
        *,
        operation_id: str,
        operation_type: str,
        entity_type: str,
        entity_id: int | None = None,
        status: str = "started",
        before_json: str | None = None,
        after_json: str | None = None,
        error_message: str | None = None,
    ) -> OperationJournal:
        entry = OperationJournal(
            operation_id=operation_id,
            operation_type=operation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            before_json=before_json,
            after_json=after_json,
            error_message=error_message,
            created_at=utcnow(),
        )
        if status in {"succeeded", "failed", "needs_recovery"}:
            entry.finished_at = utcnow()
        session.add(entry)
        session.flush()
        return entry

    def list_journal_by_operation(
        self, session: Session, operation_id: str
    ) -> list[OperationJournal]:
        return list(
            session.scalars(
                select(OperationJournal)
                .where(OperationJournal.operation_id == operation_id)
                .order_by(OperationJournal.created_at.asc(), OperationJournal.id.asc())
            )
        )

    # ——— FilePathHistory ————————————————————————————————————

    def append_path_history(
        self,
        session: Session,
        *,
        file_id: int,
        new_path: str,
        reason: str,
        old_path: str | None = None,
        operation_journal_id: int | None = None,
    ) -> FilePathHistory:
        entry = FilePathHistory(
            file_id=file_id,
            old_path=old_path,
            new_path=new_path,
            reason=reason,
            operation_journal_id=operation_journal_id,
            created_at=utcnow(),
        )
        session.add(entry)
        session.flush()
        return entry

    # ——— ImportObjectCandidate ———————————————————————————————

    def create_object_candidate(
        self,
        session: Session,
        *,
        import_batch_id: int,
        source_root_path: str,
        inbox_root_path: str,
        suggested_object_type: str | None = None,
        confidence: str | None = None,
        member_count: int = 0,
        reason_json: str | None = None,
    ) -> ImportObjectCandidate:
        now = utcnow()
        candidate = ImportObjectCandidate(
            import_batch_id=import_batch_id,
            source_root_path=source_root_path,
            inbox_root_path=inbox_root_path,
            suggested_object_type=suggested_object_type,
            confidence=confidence,
            status="detected",
            member_count=member_count,
            reason_json=reason_json,
            created_at=now,
            updated_at=now,
        )
        session.add(candidate)
        session.flush()
        return candidate

    def get_object_candidate(
        self, session: Session, candidate_id: int
    ) -> ImportObjectCandidate | None:
        return session.get(ImportObjectCandidate, candidate_id)

    def list_object_candidates(
        self, session: Session, *, page: int = 1, page_size: int = 50, status: str | None = None
    ) -> tuple[list[ImportObjectCandidate], int]:
        stmts = []
        if status is not None:
            stmts.append(ImportObjectCandidate.status == status)
        base = (
            select(ImportObjectCandidate).where(*stmts)
            if stmts
            else select(ImportObjectCandidate)
        )
        total = session.scalar(select(func.count()).select_from(base.subquery()))
        offset = (page - 1) * page_size
        items = list(
            session.scalars(
                base.order_by(
                    ImportObjectCandidate.created_at.desc(),
                    ImportObjectCandidate.id.desc(),
                )
                .offset(offset)
                .limit(page_size)
            )
        )
        return items, total or 0

    # ——— ImportObjectMember ———————————————————————————

    def create_object_member(
        self,
        session: Session,
        *,
        import_object_candidate_id: int,
        inbox_item_id: int,
        role: str = "unknown_child",
        confidence: str | None = None,
        reason: str | None = None,
    ) -> ImportObjectMember:
        member = ImportObjectMember(
            import_object_candidate_id=import_object_candidate_id,
            inbox_item_id=inbox_item_id,
            role=role,
            confidence=confidence,
            reason=reason,
            created_at=utcnow(),
        )
        session.add(member)
        session.flush()
        return member

    def list_object_members(
        self, session: Session, candidate_id: int
    ) -> list[ImportObjectMember]:
        return list(
            session.scalars(
                select(ImportObjectMember).where(
                    ImportObjectMember.import_object_candidate_id == candidate_id
                )
            )
        )
