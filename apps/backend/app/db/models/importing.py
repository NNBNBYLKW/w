from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.db.models.organize import OrganizeCandidate  # noqa: F401  ensure FK target table is registered


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="created")
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    import_method: Mapped[str] = mapped_column(String, nullable=False, default="copy")
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String, nullable=True)


class InboxItem(Base):
    __tablename__ = "inbox_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    source_path: Mapped[str] = mapped_column(String, nullable=False)
    inbox_path: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="imported")
    detected_file_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    detected_placement: Mapped[str | None] = mapped_column(String, nullable=True)
    detected_object_type: Mapped[str | None] = mapped_column(String, nullable=True)
    final_object_type: Mapped[str | None] = mapped_column(String, nullable=True)
    target_library_root_id: Mapped[int | None] = mapped_column(ForeignKey("library_roots.id"), nullable=True)
    organize_candidate_id: Mapped[int | None] = mapped_column(ForeignKey("organize_candidates.id", ondelete="SET NULL"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class OperationJournal(Base):
    __tablename__ = "operation_journal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation_id: Mapped[str] = mapped_column(String, nullable=False)
    operation_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="started")
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FilePathHistory(Base):
    __tablename__ = "file_path_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    old_path: Mapped[str | None] = mapped_column(String, nullable=True)
    new_path: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    operation_journal_id: Mapped[int | None] = mapped_column(ForeignKey("operation_journal.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ImportObjectCandidate(Base):
    __tablename__ = "import_object_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    source_root_path: Mapped[str] = mapped_column(String, nullable=False)
    inbox_root_path: Mapped[str] = mapped_column(String, nullable=False)
    suggested_object_type: Mapped[str | None] = mapped_column(String, nullable=True)
    final_object_type: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="detected")
    primary_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"), nullable=True)
    launch_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"), nullable=True)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_library_root_id: Mapped[int | None] = mapped_column(ForeignKey("library_roots.id"), nullable=True)
    organize_candidate_id: Mapped[int | None] = mapped_column(ForeignKey("organize_candidates.id", ondelete="SET NULL"), nullable=True)
    organize_plan_id: Mapped[int | None] = mapped_column(ForeignKey("organize_plans.id"), nullable=True)
    reason_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ImportObjectMember(Base):
    __tablename__ = "import_object_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_object_candidate_id: Mapped[int] = mapped_column(ForeignKey("import_object_candidates.id"), nullable=False)
    inbox_item_id: Mapped[int] = mapped_column(ForeignKey("inbox_items.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="unknown_child")
    confidence: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
