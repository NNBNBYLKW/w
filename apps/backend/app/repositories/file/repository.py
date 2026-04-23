from datetime import datetime
from itertools import islice
from typing import Iterable

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, aliased

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

    def list_indexed_files(
        self,
        session: Session,
        *,
        file_type: str | None = None,
        source_id: int | None,
        parent_path: str | None,
        tag_id: int | None,
        color_tag: str | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[File], int]:
        filters = [File.is_deleted.is_(False)]
        if file_type is not None:
            filters.append(File.file_type == file_type)
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
        tag_id: int | None,
        color_tag: str | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[File], int]:
        filters = [File.is_deleted.is_(False)]
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

    def list_media_files(
        self,
        session: Session,
        *,
        view_scope: str,
        tag_id: int | None,
        color_tag: str | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[File, bool, int | None]], int]:
        color_meta = aliased(FileUserMeta)
        filters = [
            File.is_deleted.is_(False),
            File.file_type.in_(("image", "video")),
        ]
        if view_scope != "all":
            filters.append(File.file_type == view_scope)
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
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[File, bool, int | None]], int]:
        color_meta = aliased(FileUserMeta)
        filters = [
            File.is_deleted.is_(False),
            func.lower(File.extension).in_(("epub", "pdf")),
        ]
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
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[File, bool, int | None]], int]:
        color_meta = aliased(FileUserMeta)
        normalized_extension = func.ltrim(func.lower(func.coalesce(File.extension, "")), ".")
        filters = [
            File.is_deleted.is_(False),
            normalized_extension.in_(("exe", "msi", "zip")),
        ]
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
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[File, str | None, bool, int | None]], int]:
        normalized_extension = func.ltrim(func.lower(func.coalesce(File.extension, "")), ".")
        lowered_path = func.lower(func.coalesce(File.path, ""))
        lowered_name = func.lower(func.coalesce(File.name, ""))
        lowered_stem = func.lower(func.coalesce(File.stem, ""))
        status_meta = aliased(FileUserMeta)
        color_meta = aliased(FileUserMeta)

        game_path_hints = (
            "\\games\\",
            "\\game\\",
            "\\steam\\",
            "\\steamapps\\",
            "\\gog\\",
            "\\epic games\\",
            "\\itch\\",
            "\\riot games\\",
            "\\blizzard\\",
            "\\battle.net\\",
            "\\ubisoft\\",
            "\\rockstar games\\",
            "\\ea games\\",
        )
        excluded_name_hints = (
            "setup",
            "install",
            "installer",
            "unins",
            "uninstall",
            "update",
            "updater",
            "patch",
            "redist",
        )

        game_path_filter = or_(*[lowered_path.like(f"%{hint}%") for hint in game_path_hints])
        excluded_name_filter = or_(
            *[
                or_(lowered_name.like(f"%{hint}%"), lowered_stem.like(f"%{hint}%"))
                for hint in excluded_name_hints
            ]
        )

        filters = [
            File.is_deleted.is_(False),
            or_(
                normalized_extension == "lnk",
                and_(
                    normalized_extension == "exe",
                    game_path_filter,
                    ~excluded_name_filter,
                ),
            ),
        ]
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
            )
            .outerjoin(FileUserMeta, FileUserMeta.file_id == File.id)
            .where(*filters)
            .order_by(ordered_primary, File.path.asc(), File.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        items = [(row[0], row[1], bool(row[2]), row[3]) for row in session.execute(statement).all()]

        total_statement = select(func.count()).select_from(File).where(*filters)
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
            .where(*filters)
            .order_by(ordered_primary, File.path.asc(), File.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(session.scalars(statement))

        total_statement = select(func.count()).select_from(File).where(*filters)
        total = int(session.scalar(total_statement) or 0)
        return items, total

    def _select_files_with_user_meta(
        self,
        session: Session,
        *,
        filters: list,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[File, bool, int | None]], int]:
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
            select(File, func.coalesce(FileUserMeta.is_favorite, False), FileUserMeta.rating)
            .outerjoin(FileUserMeta, FileUserMeta.file_id == File.id)
            .where(*filters)
            .order_by(ordered_primary, File.path.asc(), File.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        items = [(row[0], bool(row[1]), row[2]) for row in session.execute(statement).all()]

        total_statement = select(func.count()).select_from(File).where(*filters)
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
