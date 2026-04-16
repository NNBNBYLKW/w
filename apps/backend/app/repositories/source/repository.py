from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.source import Source


class SourceRepository:
    def list_sources(self, session: Session) -> list[Source]:
        statement = select(Source).order_by(Source.created_at.desc())
        return list(session.scalars(statement))

    def get_by_id(self, session: Session, source_id: int) -> Source | None:
        return session.get(Source, source_id)

    def get_by_path(self, session: Session, path: str) -> Source | None:
        statement = select(Source).where(Source.path == path)
        return session.scalar(statement)

    def list_other_sources(self, session: Session, source_id: int) -> list[Source]:
        statement = select(Source).where(Source.id != source_id).order_by(Source.created_at.desc())
        return list(session.scalars(statement))

    def add(self, session: Session, source: Source) -> Source:
        session.add(source)
        session.flush()
        return source

    def delete(self, session: Session, source: Source) -> None:
        session.delete(source)
