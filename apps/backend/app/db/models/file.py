from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.classification import classify_file
from app.db.models.base import Base


class File(Base):
    __tablename__ = "files"

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if "file_kind" not in kwargs or "auto_placement" not in kwargs:
            classification = classify_file(
                kwargs.get("extension"),
                kwargs.get("path"),
            )
            if "file_kind" not in kwargs:
                self.file_kind = classification.file_kind
            if "auto_placement" not in kwargs:
                self.auto_placement = classification.auto_placement

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    parent_path: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    stem: Mapped[str | None] = mapped_column(String, nullable=True)
    extension: Mapped[str | None] = mapped_column(String, nullable=True)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    file_kind: Mapped[str] = mapped_column(String, nullable=False, default="other", server_default="other")
    auto_placement: Mapped[str] = mapped_column(String, nullable=False, default="none", server_default="none")
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at_fs: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    modified_at_fs: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checksum_hint: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    storage_state: Mapped[str] = mapped_column(String, nullable=False, default="external", server_default="external")
    managed_root_id: Mapped[int | None] = mapped_column(ForeignKey("library_roots.id"), nullable=True)
    original_path: Mapped[str | None] = mapped_column(String, nullable=True)
    inbox_item_id: Mapped[int | None] = mapped_column(ForeignKey("inbox_items.id", ondelete="SET NULL"), nullable=True)
    managed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
