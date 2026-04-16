from datetime import datetime
from itertools import islice
from typing import Iterable

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models.file import File
from app.workers.scanning.scanner import DiscoveredFileRecord


class FileRepository:
    chunk_size = 250

    def get_by_id(self, session: Session, file_id: int) -> File | None:
        return session.get(File, file_id)

    def get_latest_last_seen_at_for_source(self, session: Session, source_id: int) -> datetime | None:
        statement = select(func.max(File.last_seen_at)).where(File.source_id == source_id)
        return session.scalar(statement)

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
        source_id: int | None,
        parent_path: str | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[File], int]:
        filters = [File.is_deleted.is_(False)]
        if source_id is not None:
            filters.append(File.source_id == source_id)
        if parent_path is not None:
            filters.append(func.lower(File.parent_path) == parent_path.lower())
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
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[File], int]:
        filters = [
            File.is_deleted.is_(False),
            File.file_type.in_(("image", "video")),
        ]
        if view_scope != "all":
            filters.append(File.file_type == view_scope)

        return self._select_files(
            session,
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

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
