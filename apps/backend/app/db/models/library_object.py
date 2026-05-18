from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class LibraryObject(Base):
    __tablename__ = "library_objects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_type: Mapped[str] = mapped_column(String, nullable=False)
    type_prefix: Mapped[str] = mapped_column(String, nullable=False)
    root_path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    root_name: Mapped[str] = mapped_column(String, nullable=False)
    filesystem_title: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    original_title: Mapped[str | None] = mapped_column(String, nullable=True)
    romanized_title: Mapped[str | None] = mapped_column(String, nullable=True)
    localized_title_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_title: Mapped[str | None] = mapped_column(String, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_path: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_source: Mapped[str] = mapped_column(String, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_scanned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class LibraryObjectMember(Base):
    __tablename__ = "library_object_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("library_objects.id", ondelete="CASCADE"), nullable=False)
    file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    relative_path: Mapped[str] = mapped_column(String, nullable=False)
    absolute_path: Mapped[str] = mapped_column(String, nullable=False)
    member_role: Mapped[str] = mapped_column(String, nullable=False)
    sort_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hidden_from_global: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    extension: Mapped[str | None] = mapped_column(String, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    modified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    member_status: Mapped[str] = mapped_column(String, nullable=False, default="active", server_default="active")


class AssetMetadataCache(Base):
    __tablename__ = "asset_metadata_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("library_objects.id", ondelete="CASCADE"), unique=True, nullable=False)
    yaml_path: Mapped[str | None] = mapped_column(String, nullable=True)
    schema_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parsed_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(String, nullable=False)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
