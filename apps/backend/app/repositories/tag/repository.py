from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.tag import Tag


class TagRepository:
    def get_by_id(self, session: Session, tag_id: int) -> Tag | None:
        return session.get(Tag, tag_id)

    def get_by_normalized_name(self, session: Session, normalized_name: str) -> Tag | None:
        statement = select(Tag).where(Tag.normalized_name == normalized_name)
        return session.scalars(statement).first()

    def list_tags(self, session: Session) -> list[Tag]:
        statement = select(Tag).order_by(Tag.normalized_name.asc(), Tag.id.asc())
        return list(session.scalars(statement))

    def add(self, session: Session, tag: Tag) -> None:
        session.add(tag)
        session.flush()
