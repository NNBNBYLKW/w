from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.db.models.file import File
from app.db.models.library_object import AssetMetadataCache, LibraryObject, LibraryObjectMember


@dataclass(frozen=True)
class LibraryObjectListFilters:
    page: int = 1
    page_size: int = 50
    object_type: str | None = None
    needs_review: bool | None = None
    query: str | None = None
    sort_by: str = "last_scanned_at"
    sort_order: str = "desc"


class LibraryObjectRepository:
    def get_by_id(self, session: Session, object_id: int) -> LibraryObject | None:
        return session.get(LibraryObject, object_id)

    def get_by_root_path(self, session: Session, root_path: str) -> LibraryObject | None:
        return session.scalar(select(LibraryObject).where(LibraryObject.root_path == root_path))

    def add(self, session: Session, library_object: LibraryObject) -> LibraryObject:
        session.add(library_object)
        session.flush()
        return library_object

    def delete_members(self, session: Session, object_id: int) -> None:
        session.query(LibraryObjectMember).filter(LibraryObjectMember.object_id == object_id).delete()

    def add_members(self, session: Session, members: list[LibraryObjectMember]) -> None:
        session.add_all(members)
        session.flush()

    def upsert_asset_metadata(self, session: Session, metadata: AssetMetadataCache) -> AssetMetadataCache:
        existing = session.scalar(select(AssetMetadataCache).where(AssetMetadataCache.object_id == metadata.object_id))
        if existing is None:
            session.add(metadata)
            session.flush()
            return metadata
        existing.yaml_path = metadata.yaml_path
        existing.schema_version = metadata.schema_version
        existing.parsed_json = metadata.parsed_json
        existing.parse_status = metadata.parse_status
        existing.parse_error = metadata.parse_error
        existing.updated_at = metadata.updated_at
        session.flush()
        return existing

    def get_asset_metadata(self, session: Session, object_id: int) -> AssetMetadataCache | None:
        return session.scalar(select(AssetMetadataCache).where(AssetMetadataCache.object_id == object_id))

    def get_file_id_by_path(self, session: Session, path: str) -> int | None:
        return session.scalar(select(File.id).where(File.path == path))

    def list_objects(self, session: Session, filters: LibraryObjectListFilters) -> tuple[list[LibraryObject], int]:
        statement = self._apply_filters(select(LibraryObject), filters)
        count_statement = self._apply_filters(select(func.count(LibraryObject.id)), filters)
        total = int(session.scalar(count_statement) or 0)

        sort_column = {
            "title": LibraryObject.title,
            "object_type": LibraryObject.object_type,
            "root_path": LibraryObject.root_path,
            "updated_at": LibraryObject.updated_at,
            "last_scanned_at": LibraryObject.last_scanned_at,
        }.get(filters.sort_by, LibraryObject.last_scanned_at)
        if filters.sort_order == "asc":
            statement = statement.order_by(sort_column.asc(), LibraryObject.id.asc())
        else:
            statement = statement.order_by(sort_column.desc(), LibraryObject.id.desc())

        offset = max(filters.page - 1, 0) * filters.page_size
        items = list(session.scalars(statement.offset(offset).limit(filters.page_size)))
        return items, total

    def count_members(self, session: Session, object_id: int, role: str | None = None) -> int:
        statement = select(func.count(LibraryObjectMember.id)).where(LibraryObjectMember.object_id == object_id)
        if role:
            statement = statement.where(LibraryObjectMember.member_role == role)
        return int(session.scalar(statement) or 0)

    def list_members(
        self,
        session: Session,
        object_id: int,
        *,
        page: int = 1,
        page_size: int = 50,
        role: str | None = None,
    ) -> tuple[list[LibraryObjectMember], int]:
        statement = select(LibraryObjectMember).where(LibraryObjectMember.object_id == object_id)
        if role:
            statement = statement.where(LibraryObjectMember.member_role == role)
        total = self.count_members(session, object_id, role)
        offset = max(page - 1, 0) * page_size
        statement = statement.order_by(
            LibraryObjectMember.sort_index.asc().nulls_last(),
            LibraryObjectMember.relative_path.asc(),
        )
        return list(session.scalars(statement.offset(offset).limit(page_size))), total

    def member_counts_for_objects(self, session: Session, object_ids: list[int]) -> dict[int, int]:
        if not object_ids:
            return {}
        rows = session.execute(
            select(LibraryObjectMember.object_id, func.count(LibraryObjectMember.id))
            .where(LibraryObjectMember.object_id.in_(object_ids))
            .group_by(LibraryObjectMember.object_id)
        ).all()
        return {int(object_id): int(count) for object_id, count in rows}

    def overview_counts(self, session: Session) -> dict[str, object]:
        total = int(session.scalar(select(func.count(LibraryObject.id))) or 0)
        needs_review = int(
            session.scalar(select(func.count(LibraryObject.id)).where(LibraryObject.needs_review.is_(True))) or 0
        )
        unknown = int(
            session.scalar(select(func.count(LibraryObject.id)).where(LibraryObject.object_type == "unknown_object"))
            or 0
        )
        last_scan = session.scalar(select(func.max(LibraryObject.last_scanned_at)))
        type_rows = session.execute(
            select(LibraryObject.object_type, func.count(LibraryObject.id)).group_by(LibraryObject.object_type)
        ).all()
        ok_yaml = int(
            session.scalar(select(func.count(AssetMetadataCache.id)).where(AssetMetadataCache.parse_status == "ok"))
            or 0
        )
        invalid_yaml = int(
            session.scalar(
                select(func.count(AssetMetadataCache.id)).where(AssetMetadataCache.parse_status == "invalid_yaml")
            )
            or 0
        )
        return {
            "total_objects": total,
            "needs_review_count": needs_review,
            "unknown_object_count": unknown,
            "last_object_scan_at": last_scan,
            "object_type_counts": {str(object_type): int(count) for object_type, count in type_rows},
            "asset_yaml_ok_count": ok_yaml,
            "asset_yaml_invalid_count": invalid_yaml,
        }

    def _apply_filters(self, statement: Select, filters: LibraryObjectListFilters) -> Select:
        if filters.object_type:
            statement = statement.where(LibraryObject.object_type == filters.object_type)
        if filters.needs_review is not None:
            statement = statement.where(LibraryObject.needs_review.is_(filters.needs_review))
        if filters.query:
            pattern = f"%{filters.query.strip()}%"
            statement = statement.where(
                or_(
                    LibraryObject.title.like(pattern),
                    LibraryObject.filesystem_title.like(pattern),
                    LibraryObject.root_name.like(pattern),
                    LibraryObject.root_path.like(pattern),
                )
            )
        return statement
