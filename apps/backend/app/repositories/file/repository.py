from datetime import datetime
from itertools import islice
from typing import Iterable

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, aliased

from app.core.classification import classify_file
from app.core.time import utcnow
from app.db.models.file import File
from app.db.models.file_tag import FileTag
from app.db.models.file_user_meta import FileUserMeta
from app.workers.scanning.scanner import DiscoveredFileRecord


class FileRepository:
    chunk_size = 250

    def get_by_id(self, session: Session, file_id: int) -> File | None:
        return session.get(File, file_id)

    def list_active_files_by_ids(self, session: Session, file_ids: list[int]) -> list[File]:
        if not file_ids:
            return []

        statement = (
            select(File)
            .where(File.id.in_(file_ids))
            .where(File.is_deleted.is_(False))
            .order_by(File.id.asc())
        )
        return list(session.scalars(statement))

    def get_latest_last_seen_at_for_source(self, session: Session, source_id: int) -> datetime | None:
        statement = select(func.max(File.last_seen_at)).where(File.source_id == source_id)
        return session.scalar(statement)

    def list_seen_files_for_source_scan(
        self,
        session: Session,
        *,
        source_id: int,
        scanned_at: datetime,
    ) -> list[File]:
        statement = (
            select(File)
            .where(File.source_id == source_id)
            .where(File.last_seen_at == scanned_at)
            .where(File.is_deleted.is_(False))
            .order_by(File.id.asc())
        )
        return list(session.scalars(statement))

    def upsert_discovered_files(
        self,
        session: Session,
        source_id: int,
        records: list[DiscoveredFileRecord],
        scanned_at: datetime,
    ) -> int:
        if not records:
            return 0

        total = 0
        for chunk in self._chunked(records, self.chunk_size):
            rows = [
                {
                    "source_id": source_id,
                    "path": record.path,
                    "parent_path": record.parent_path,
                    "name": record.name,
                    "stem": record.stem,
                    "extension": record.extension,
                    "file_type": record.file_type,
                    "file_kind": record.file_kind,
                    "auto_placement": record.auto_placement,
                    "mime_type": record.mime_type,
                    "size_bytes": record.size_bytes,
                    "created_at_fs": record.created_at_fs,
                    "modified_at_fs": record.modified_at_fs,
                    "discovered_at": scanned_at,
                    "last_seen_at": scanned_at,
                    "is_deleted": False,
                    "checksum_hint": None,
                    "updated_at": scanned_at,
                }
                for record in chunk
            ]
            insert_statement = sqlite_insert(File).values(rows)
            upsert_statement = insert_statement.on_conflict_do_update(
                index_elements=[File.path],
                set_={
                    "source_id": insert_statement.excluded.source_id,
                    "parent_path": insert_statement.excluded.parent_path,
                    "name": insert_statement.excluded.name,
                    "stem": insert_statement.excluded.stem,
                    "extension": insert_statement.excluded.extension,
                    "file_type": insert_statement.excluded.file_type,
                    "file_kind": insert_statement.excluded.file_kind,
                    "auto_placement": insert_statement.excluded.auto_placement,
                    "mime_type": insert_statement.excluded.mime_type,
                    "size_bytes": insert_statement.excluded.size_bytes,
                    "created_at_fs": insert_statement.excluded.created_at_fs,
                    "modified_at_fs": insert_statement.excluded.modified_at_fs,
                    "last_seen_at": insert_statement.excluded.last_seen_at,
                    "is_deleted": insert_statement.excluded.is_deleted,
                    "checksum_hint": insert_statement.excluded.checksum_hint,
                    "updated_at": insert_statement.excluded.updated_at,
                },
            )
            session.execute(upsert_statement)
            total += len(rows)

        session.flush()
        return total

    def bulk_upsert_files(
        self,
        session: Session,
        records: list[DiscoveredFileRecord],
        scanned_at: datetime | None = None,
    ) -> None:
        now = scanned_at or utcnow()
        values = [
            {
                "path": r.path,
                "parent_path": r.parent_path,
                "name": r.name,
                "extension": r.extension,
                "file_type": r.file_type,
                "file_kind": r.file_kind,
                "auto_placement": r.auto_placement,
                "size_bytes": r.size_bytes,
                "modified_at_fs": r.modified_at_fs,
                "created_at_fs": r.created_at_fs,
                "source_id": r.source_id,
                "discovered_at": now,
                "last_seen_at": now,
                "updated_at": now,
                "is_deleted": False,
            }
            for r in records
        ]
        stmt = sqlite_insert(File).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["path"],
            set_={
                "last_seen_at": now,
                "size_bytes": stmt.excluded.size_bytes,
                "modified_at_fs": stmt.excluded.modified_at_fs,
            },
        )
        session.execute(stmt)
        session.flush()

    def mark_unseen_files_deleted(self, session: Session, source_id: int, scanned_at: datetime) -> int:
        statement = (
            update(File)
            .where(File.source_id == source_id)
            .where(File.last_seen_at < scanned_at)
            .where(File.is_deleted.is_(False))
            .values(is_deleted=True, updated_at=scanned_at)
        )
        result = session.execute(statement)
        session.flush()
        return int(result.rowcount or 0)

    def count_indexed_files(
        self,
        session: Session,
        *,
        file_type: str | None = None,
        file_kind: str | None,
        source_id: int | None,
        parent_path: str | None,
        storage_state: str | None = None,
        tag_id: int | None,
        color_tag: str | None,
    ) -> int:
        filters = [File.is_deleted.is_(False)]
        if storage_state is not None:
            filters.append(File.storage_state == storage_state)
        if file_type is not None:
            filters.append(File.file_type == file_type)
        if file_kind is not None:
            filters.append(File.file_kind == file_kind)
        if source_id is not None:
            filters.append(File.source_id == source_id)
        if parent_path is not None:
            filters.append(func.lower(File.parent_path) == parent_path.lower())
        if tag_id is not None:
            filters.append(
                select(1)
                .select_from(FileTag)
                .where(FileTag.file_id == File.id, FileTag.tag_id == tag_id)
                .exists()
            )
        if color_tag is not None:
            filters.append(
                select(1)
                .select_from(FileUserMeta)
                .where(
                    FileUserMeta.file_id == File.id,
                    FileUserMeta.color_tag == color_tag,
                )
                .exists()
            )
        total_statement = select(func.count()).select_from(File).where(*filters)
        return int(session.scalar(total_statement) or 0)

    def aggregate_indexed_files(
        self,
        session: Session,
        *,
        file_type: str | None = None,
        file_kind: str | None,
        source_id: int | None,
        parent_path: str | None,
        storage_state: str | None = None,
        tag_id: int | None,
        color_tag: str | None,
    ) -> dict:
        filters = [File.is_deleted.is_(False)]
        if storage_state is not None:
            filters.append(File.storage_state == storage_state)
        if file_type is not None:
            filters.append(File.file_type == file_type)
        if file_kind is not None:
            filters.append(File.file_kind == file_kind)
        if source_id is not None:
            filters.append(File.source_id == source_id)
        if parent_path is not None:
            filters.append(func.lower(File.parent_path) == parent_path.lower())
        if tag_id is not None:
            filters.append(
                select(1)
                .select_from(FileTag)
                .where(FileTag.file_id == File.id, FileTag.tag_id == tag_id)
                .exists()
            )
        if color_tag is not None:
            filters.append(
                select(1)
                .select_from(FileUserMeta)
                .where(
                    FileUserMeta.file_id == File.id,
                    FileUserMeta.color_tag == color_tag,
                )
                .exists()
            )
        stmt = select(
            func.count().label("total_files"),
            func.sum(File.size_bytes).label("total_size_bytes"),
            func.min(File.modified_at_fs).label("oldest_file_at"),
            func.max(File.modified_at_fs).label("newest_file_at"),
        ).where(*filters)
        row = session.execute(stmt).one()
        return dict(row._mapping)

    def list_indexed_files(
        self,
        session: Session,
        *,
        file_type: str | None = None,
        file_kind: str | None,
        source_id: int | None,
        parent_path: str | None,
        storage_state: str | None = None,
        tag_id: int | None,
        color_tag: str | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[File], int]:
        filters = [File.is_deleted.is_(False)]
        if storage_state is not None:
            filters.append(File.storage_state == storage_state)
        if file_type is not None:
            filters.append(File.file_type == file_type)
        if file_kind is not None:
            filters.append(File.file_kind == file_kind)
        if source_id is not None:
            filters.append(File.source_id == source_id)
        if parent_path is not None:
            filters.append(func.lower(File.parent_path) == parent_path.lower())
        if tag_id is not None:
            filters.append(
                select(1)
                .select_from(FileTag)
                .where(FileTag.file_id == File.id, FileTag.tag_id == tag_id)
                .exists()
            )
        if color_tag is not None:
            filters.append(
                select(1)
                .select_from(FileUserMeta)
                .where(
                    FileUserMeta.file_id == File.id,
                    FileUserMeta.color_tag == color_tag,
                )
                .exists()
            )
        return self._select_files(
            session,
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def search_indexed_files(
        self,
        session: Session,
        *,
        query: str | None,
        file_type: str | None,
        file_kind: str | None,
        library_placement: str | None,
        storage_state: str | None = None,
        tag_id: int | None,
        color_tag: str | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[File], int]:
        filters = [File.is_deleted.is_(False)]
        if storage_state is not None:
            filters.append(File.storage_state == storage_state)
        if query is not None:
            pattern = f"%{query.lower()}%"
            filters.append(
                or_(
                    func.lower(File.name).like(pattern),
                    func.lower(File.path).like(pattern),
                )
            )
        if file_type is not None:
            filters.append(File.file_type == file_type)
        if file_kind is not None:
            filters.append(File.file_kind == file_kind)
        needs_user_meta_join = False
        if library_placement is not None:
            filters.append(self._effective_placement_expr() == library_placement)
            needs_user_meta_join = True
        if tag_id is not None:
            filters.append(
                select(1)
                .select_from(FileTag)
                .where(FileTag.file_id == File.id, FileTag.tag_id == tag_id)
                .exists()
            )
        if color_tag is not None:
            filters.append(
                select(1)
                .select_from(FileUserMeta)
                .where(
                    FileUserMeta.file_id == File.id,
                    FileUserMeta.color_tag == color_tag,
                )
                .exists()
            )

        return self._select_files(
            session,
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            join_user_meta=needs_user_meta_join,
        )

    def list_media_files(
        self,
        session: Session,
        *,
        view_scope: str,
        tag_id: int | None,
        color_tag: str | None,
        storage_state: str | None = None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[File, bool, int | None, str | None]], int]:
        color_meta = aliased(FileUserMeta)
        placement_expr = self._effective_placement_expr()
        filters = [
            File.is_deleted.is_(False),
            placement_expr == "media",
        ]
        if storage_state is not None:
            filters.append(File.storage_state == storage_state)
        if view_scope != "all":
            filters.append(File.file_kind == view_scope)
        if tag_id is not None:
            filters.append(
                select(1)
                .select_from(FileTag)
                .where(FileTag.file_id == File.id, FileTag.tag_id == tag_id)
                .exists()
            )
        if color_tag is not None:
            filters.append(
                select(1)
                .select_from(color_meta)
                .where(
                    color_meta.file_id == File.id,
                    color_meta.color_tag == color_tag,
                )
                .exists()
            )

        return self._select_files_with_user_meta(
            session,
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def list_book_files(
        self,
        session: Session,
        *,
        tag_id: int | None,
        color_tag: str | None,
        storage_state: str | None = None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[File, bool, int | None, str | None]], int]:
        color_meta = aliased(FileUserMeta)
        filters = [
            File.is_deleted.is_(False),
            self._effective_placement_expr() == "books",
        ]
        if storage_state is not None:
            filters.append(File.storage_state == storage_state)
        if tag_id is not None:
            filters.append(
                select(1)
                .select_from(FileTag)
                .where(FileTag.file_id == File.id, FileTag.tag_id == tag_id)
                .exists()
            )
        if color_tag is not None:
            filters.append(
                select(1)
                .select_from(color_meta)
                .where(
                    color_meta.file_id == File.id,
                    color_meta.color_tag == color_tag,
                )
                .exists()
            )

        return self._select_files_with_user_meta(
            session,
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def list_software_files(
        self,
        session: Session,
        *,
        tag_id: int | None,
        color_tag: str | None,
        storage_state: str | None = None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[File, bool, int | None, str | None]], int]:
        color_meta = aliased(FileUserMeta)
        filters = [
            File.is_deleted.is_(False),
            self._effective_placement_expr() == "software",
        ]
        if storage_state is not None:
            filters.append(File.storage_state == storage_state)
        if tag_id is not None:
            filters.append(
                select(1)
                .select_from(FileTag)
                .where(FileTag.file_id == File.id, FileTag.tag_id == tag_id)
                .exists()
            )
        if color_tag is not None:
            filters.append(
                select(1)
                .select_from(color_meta)
                .where(
                    color_meta.file_id == File.id,
                    color_meta.color_tag == color_tag,
                )
                .exists()
            )

        return self._select_files_with_user_meta(
            session,
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def list_game_files(
        self,
        session: Session,
        *,
        tag_id: int | None,
        color_tag: str | None,
        status: str | None,
        storage_state: str | None = None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[File, str | None, bool, int | None, str | None]], int]:
        status_meta = aliased(FileUserMeta)
        color_meta = aliased(FileUserMeta)

        filters = [
            File.is_deleted.is_(False),
            self._effective_placement_expr() == "games",
        ]
        if storage_state is not None:
            filters.append(File.storage_state == storage_state)
        if status is not None:
            filters.append(
                select(1)
                .select_from(status_meta)
                .where(
                    status_meta.file_id == File.id,
                    status_meta.status == status,
                )
                .exists()
            )
        if tag_id is not None:
            filters.append(
                select(1)
                .select_from(FileTag)
                .where(FileTag.file_id == File.id, FileTag.tag_id == tag_id)
                .exists()
            )
        if color_tag is not None:
            filters.append(
                select(1)
                .select_from(color_meta)
                .where(color_meta.file_id == File.id, color_meta.color_tag == color_tag)
                .exists()
            )

        modified_expr = func.coalesce(File.modified_at_fs, File.discovered_at)
        if sort_by == "name":
            primary_order = func.lower(File.name)
        elif sort_by == "discovered_at":
            primary_order = File.discovered_at
        else:
            primary_order = modified_expr

        ordered_primary = primary_order.asc() if sort_order == "asc" else primary_order.desc()
        offset = (page - 1) * page_size

        statement = (
            select(
                File,
                FileUserMeta.status,
                func.coalesce(FileUserMeta.is_favorite, False),
                FileUserMeta.rating,
                FileUserMeta.manual_placement,
            )
            .outerjoin(FileUserMeta, FileUserMeta.file_id == File.id)
            .where(*filters)
            .order_by(ordered_primary, File.path.asc(), File.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        items = [(row[0], row[1], bool(row[2]), row[3], row[4]) for row in session.execute(statement).all()]

        total_statement = (
            select(func.count())
            .select_from(File)
            .outerjoin(FileUserMeta, FileUserMeta.file_id == File.id)
            .where(*filters)
        )
        total = int(session.scalar(total_statement) or 0)
        return items, total

    def list_recent_files(
        self,
        session: Session,
        *,
        cutoff: datetime,
        now: datetime,
        page: int,
        page_size: int,
        sort_order: str,
    ) -> tuple[list[File], int]:
        filters = [
            File.is_deleted.is_(False),
            File.discovered_at >= cutoff,
            File.discovered_at <= now,
        ]

        return self._select_files(
            session,
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by="discovered_at",
            sort_order=sort_order,
        )

    def list_recent_tagged_files(
        self,
        session: Session,
        *,
        cutoff: datetime,
        now: datetime,
        page: int,
        page_size: int,
        sort_order: str,
    ) -> tuple[list[tuple[File, datetime]], int]:
        latest_tagged_subquery = (
            select(
                FileTag.file_id.label("file_id"),
                func.max(FileTag.created_at).label("occurred_at"),
            )
            .group_by(FileTag.file_id)
            .subquery()
        )
        filters = [
            File.is_deleted.is_(False),
            latest_tagged_subquery.c.occurred_at >= cutoff,
            latest_tagged_subquery.c.occurred_at <= now,
        ]
        return self._select_files_with_occurrence(
            session,
            occurrence_subquery=latest_tagged_subquery,
            filters=filters,
            occurrence_column=latest_tagged_subquery.c.occurred_at,
            page=page,
            page_size=page_size,
            sort_order=sort_order,
        )

    def list_recent_color_tagged_files(
        self,
        session: Session,
        *,
        cutoff: datetime,
        now: datetime,
        page: int,
        page_size: int,
        sort_order: str,
    ) -> tuple[list[tuple[File, datetime]], int]:
        color_tagged_subquery = (
            select(
                FileUserMeta.file_id.label("file_id"),
                FileUserMeta.updated_at.label("occurred_at"),
            )
            .where(FileUserMeta.color_tag.is_not(None))
            .subquery()
        )
        filters = [
            File.is_deleted.is_(False),
            color_tagged_subquery.c.occurred_at >= cutoff,
            color_tagged_subquery.c.occurred_at <= now,
        ]
        return self._select_files_with_occurrence(
            session,
            occurrence_subquery=color_tagged_subquery,
            filters=filters,
            occurrence_column=color_tagged_subquery.c.occurred_at,
            page=page,
            page_size=page_size,
            sort_order=sort_order,
        )

    def list_files_for_tag(
        self,
        session: Session,
        *,
        tag_id: int,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[File], int]:
        modified_expr = func.coalesce(File.modified_at_fs, File.discovered_at)
        if sort_by == "name":
            primary_order = func.lower(File.name)
        elif sort_by == "discovered_at":
            primary_order = File.discovered_at
        else:
            primary_order = modified_expr

        ordered_primary = primary_order.asc() if sort_order == "asc" else primary_order.desc()
        offset = (page - 1) * page_size

        statement = (
            select(File)
            .join(FileTag, FileTag.file_id == File.id)
            .where(FileTag.tag_id == tag_id, File.is_deleted.is_(False))
            .order_by(ordered_primary, File.path.asc(), File.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(session.scalars(statement))

        total_statement = (
            select(func.count())
            .select_from(File)
            .join(FileTag, FileTag.file_id == File.id)
            .where(FileTag.tag_id == tag_id, File.is_deleted.is_(False))
        )
        total = int(session.scalar(total_statement) or 0)
        return items, total

    def _select_files(
        self,
        session: Session,
        *,
        filters: list,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        join_user_meta: bool = False,
    ) -> tuple[list[File], int]:
        modified_expr = func.coalesce(File.modified_at_fs, File.discovered_at)
        if sort_by == "name":
            primary_order = func.lower(File.name)
        elif sort_by == "discovered_at":
            primary_order = File.discovered_at
        else:
            primary_order = modified_expr

        ordered_primary = primary_order.asc() if sort_order == "asc" else primary_order.desc()
        offset = (page - 1) * page_size

        statement = select(File)
        if join_user_meta:
            statement = statement.outerjoin(FileUserMeta, FileUserMeta.file_id == File.id)
        statement = (
            statement.where(*filters)
            .order_by(ordered_primary, File.path.asc(), File.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(session.scalars(statement))

        total_statement = select(func.count()).select_from(File)
        if join_user_meta:
            total_statement = total_statement.outerjoin(FileUserMeta, FileUserMeta.file_id == File.id)
        total_statement = total_statement.where(*filters)
        total = int(session.scalar(total_statement) or 0)
        return items, total

    def _effective_placement_expr(self):
        return func.coalesce(FileUserMeta.manual_placement, File.auto_placement)

    def _select_files_with_user_meta(
        self,
        session: Session,
        *,
        filters: list,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[File, bool, int | None, str | None]], int]:
        modified_expr = func.coalesce(File.modified_at_fs, File.discovered_at)
        if sort_by == "name":
            primary_order = func.lower(File.name)
        elif sort_by == "discovered_at":
            primary_order = File.discovered_at
        else:
            primary_order = modified_expr

        ordered_primary = primary_order.asc() if sort_order == "asc" else primary_order.desc()
        offset = (page - 1) * page_size

        statement = (
            select(File, func.coalesce(FileUserMeta.is_favorite, False), FileUserMeta.rating, FileUserMeta.manual_placement)
            .outerjoin(FileUserMeta, FileUserMeta.file_id == File.id)
            .where(*filters)
            .order_by(ordered_primary, File.path.asc(), File.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        items = [(row[0], bool(row[1]), row[2], row[3]) for row in session.execute(statement).all()]

        total_statement = select(func.count()).select_from(File).where(*filters)
        total_statement = total_statement.outerjoin(FileUserMeta, FileUserMeta.file_id == File.id)
        total = int(session.scalar(total_statement) or 0)
        return items, total

    def _select_files_with_occurrence(
        self,
        session: Session,
        *,
        occurrence_subquery,
        filters: list,
        occurrence_column,
        page: int,
        page_size: int,
        sort_order: str,
    ) -> tuple[list[tuple[File, datetime]], int]:
        ordered_occurrence = occurrence_column.asc() if sort_order == "asc" else occurrence_column.desc()
        offset = (page - 1) * page_size

        statement = (
            select(File, occurrence_column)
            .join(occurrence_subquery, occurrence_subquery.c.file_id == File.id)
            .where(*filters)
            .order_by(ordered_occurrence, File.path.asc(), File.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        items = [(row[0], row[1]) for row in session.execute(statement).all()]

        total_statement = select(func.count()).select_from(File).join(
            occurrence_subquery,
            occurrence_subquery.c.file_id == File.id,
        ).where(*filters)
        total = int(session.scalar(total_statement) or 0)
        return items, total

    def _chunked(
        self,
        records: list[DiscoveredFileRecord],
        size: int,
    ) -> Iterable[list[DiscoveredFileRecord]]:
        iterator = iter(records)
        while True:
            chunk = list(islice(iterator, size))
            if not chunk:
                break
            yield chunk
