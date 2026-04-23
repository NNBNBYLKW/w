from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.collection import Collection


class CollectionRepository:
    def list_collections(self, session: Session) -> list[Collection]:
        statement = select(Collection).order_by(Collection.created_at.desc(), Collection.id.desc())
        return list(session.scalars(statement))

    def get_by_id(self, session: Session, collection_id: int) -> Collection | None:
        return session.get(Collection, collection_id)

    def add(self, session: Session, collection: Collection) -> Collection:
        session.add(collection)
        session.flush()
        return collection

    def save(self, session: Session, collection: Collection) -> Collection:
        session.add(collection)
        session.flush()
        return collection

    def delete(self, session: Session, collection: Collection) -> None:
        session.delete(collection)
