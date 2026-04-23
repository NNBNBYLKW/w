from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.file import File
from app.db.models.file_tag import FileTag
from app.db.models.tag import Tag


class TagRepository:
    def get_by_id(self, session: Session, tag_id: int) -> Tag | None:
        return session.get(Tag, tag_id)

    def get_by_normalized_name(self, session: Session, normalized_name: str) -> Tag | None:
        statement = select(Tag).where(Tag.normalized_name == normalized_name)
        return session.scalars(statement).first()

    def list_tags_with_active_files(self, session: Session) -> list[Tag]:
        statement = (
            select(Tag)
            .join(FileTag, FileTag.tag_id == Tag.id)
            .join(File, File.id == FileTag.file_id)
            .where(File.is_deleted.is_(False))
            .distinct()
            .order_by(Tag.normalized_name.asc(), Tag.id.asc())
        )
        return list(session.scalars(statement))

    def has_active_files(self, session: Session, tag_id: int) -> bool:
        statement = (
            select(FileTag.tag_id)
            .join(File, File.id == FileTag.file_id)
            .where(FileTag.tag_id == tag_id, File.is_deleted.is_(False))
            .limit(1)
        )
        return session.execute(statement).first() is not None

    def delete_if_orphaned(self, session: Session, tag_id: int) -> bool:
        if self.has_active_files(session, tag_id):
            return False

        tag = self.get_by_id(session, tag_id)
        if tag is None:
            return False

        session.delete(tag)
        session.flush()
        return True

    def add(self, session: Session, tag: Tag) -> None:
        session.add(tag)
        session.flush()
