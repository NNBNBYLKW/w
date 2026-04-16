from datetime import datetime

from sqlalchemy import delete, select
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

    def detach_tag(self, session: Session, file_id: int, tag_id: int) -> int:
        statement = delete(FileTag).where(FileTag.file_id == file_id, FileTag.tag_id == tag_id)
        result = session.execute(statement)
        session.flush()
        return int(result.rowcount or 0)
