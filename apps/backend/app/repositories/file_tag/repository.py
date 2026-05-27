from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models.file_tag import FileTag
from app.db.models.tag import Tag


class FileTagRepository:
    def list_tags_for_file(self, session: Session, file_id: int) -> list[Tag]:
        statement = (
            select(Tag)
            .join(FileTag, FileTag.tag_id == Tag.id)
            .where(FileTag.file_id == file_id)
            .order_by(Tag.normalized_name.asc(), Tag.id.asc())
        )
        return list(session.scalars(statement))

    def attach_tag(self, session: Session, file_id: int, tag_id: int, created_at: datetime) -> None:
        statement = (
            sqlite_insert(FileTag)
            .values(file_id=file_id, tag_id=tag_id, created_at=created_at)
            .on_conflict_do_nothing(index_elements=[FileTag.file_id, FileTag.tag_id])
        )
        session.execute(statement)
        session.flush()

    def attach_tag_to_files(self, session: Session, file_ids: list[int], tag_id: int, created_at: datetime) -> None:
        if not file_ids:
            return

        statement = (
            sqlite_insert(FileTag)
            .values(
                [
                    {
                        "file_id": file_id,
                        "tag_id": tag_id,
                        "created_at": created_at,
                    }
                    for file_id in file_ids
                ]
            )
            .on_conflict_do_nothing(index_elements=[FileTag.file_id, FileTag.tag_id])
        )
        session.execute(statement)
        session.flush()

    def detach_tag(self, session: Session, file_id: int, tag_id: int) -> int:
        statement = delete(FileTag).where(FileTag.file_id == file_id, FileTag.tag_id == tag_id)
        result = session.execute(statement)
        session.flush()
        return int(result.rowcount or 0)

    def reassign_tag(self, session: Session, source_tag_id: int, target_tag_id: int) -> None:
        """Reassign all file associations from source_tag_id to target_tag_id.

        For files already tagged with target_tag_id, the source association is removed.
        For remaining files, the source tag is replaced with the target tag.
        """
        subq = select(FileTag.file_id).where(FileTag.tag_id == target_tag_id).subquery()
        delete_dup = delete(FileTag).where(
            FileTag.tag_id == source_tag_id,
            FileTag.file_id.in_(select(subq.c.file_id)),
        )
        session.execute(delete_dup)
        update_stmt = (
            update(FileTag)
            .where(FileTag.tag_id == source_tag_id)
            .values(tag_id=target_tag_id)
        )
        session.execute(update_stmt)
        session.flush()
