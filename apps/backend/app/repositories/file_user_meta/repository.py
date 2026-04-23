from datetime import datetime

from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models.file_user_meta import FileUserMeta


class FileUserMetaRepository:
    def get_by_file_id(self, session: Session, file_id: int) -> FileUserMeta | None:
        return session.get(FileUserMeta, file_id)

    def upsert_color_tag(
        self,
        session: Session,
        file_id: int,
        color_tag: str,
        updated_at: datetime,
    ) -> None:
        insert_statement = sqlite_insert(FileUserMeta).values(
            file_id=file_id,
            color_tag=color_tag,
            status=None,
            rating=None,
            is_favorite=False,
            updated_at=updated_at,
        )
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[FileUserMeta.file_id],
            set_={
                "color_tag": insert_statement.excluded.color_tag,
                "updated_at": insert_statement.excluded.updated_at,
            },
        )
        session.execute(upsert_statement)
        session.flush()

    def upsert_color_tag_for_files(
        self,
        session: Session,
        file_ids: list[int],
        color_tag: str,
        updated_at: datetime,
    ) -> None:
        if not file_ids:
            return

        insert_statement = sqlite_insert(FileUserMeta).values(
            [
                {
                    "file_id": file_id,
                    "color_tag": color_tag,
                    "status": None,
                    "rating": None,
                    "is_favorite": False,
                    "updated_at": updated_at,
                }
                for file_id in file_ids
            ]
        )
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[FileUserMeta.file_id],
            set_={
                "color_tag": insert_statement.excluded.color_tag,
                "updated_at": insert_statement.excluded.updated_at,
            },
        )
        session.execute(upsert_statement)
        session.flush()

    def clear_color_tag(self, session: Session, file_id: int, updated_at: datetime) -> int:
        statement = (
            update(FileUserMeta)
            .where(FileUserMeta.file_id == file_id)
            .values(color_tag=None, updated_at=updated_at)
        )
        result = session.execute(statement)
        session.flush()
        return int(result.rowcount or 0)

    def clear_color_tag_for_files(self, session: Session, file_ids: list[int], updated_at: datetime) -> int:
        if not file_ids:
            return 0

        statement = (
            update(FileUserMeta)
            .where(FileUserMeta.file_id.in_(file_ids))
            .values(color_tag=None, updated_at=updated_at)
        )
        result = session.execute(statement)
        session.flush()
        return int(result.rowcount or 0)

    def upsert_status(
        self,
        session: Session,
        file_id: int,
        status: str,
        updated_at: datetime,
    ) -> None:
        insert_statement = sqlite_insert(FileUserMeta).values(
            file_id=file_id,
            color_tag=None,
            status=status,
            rating=None,
            is_favorite=False,
            updated_at=updated_at,
        )
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[FileUserMeta.file_id],
            set_={
                "status": insert_statement.excluded.status,
                "updated_at": insert_statement.excluded.updated_at,
            },
        )
        session.execute(upsert_statement)
        session.flush()

    def clear_status(self, session: Session, file_id: int, updated_at: datetime) -> int:
        statement = (
            update(FileUserMeta)
            .where(FileUserMeta.file_id == file_id)
            .values(status=None, updated_at=updated_at)
        )
        result = session.execute(statement)
        session.flush()
        return int(result.rowcount or 0)

    def update_user_meta(
        self,
        session: Session,
        file_id: int,
        *,
        is_favorite_provided: bool,
        is_favorite: bool | None,
        rating_provided: bool,
        rating: int | None,
        updated_at: datetime,
    ) -> None:
        current = self.get_by_file_id(session, file_id)
        next_color_tag = current.color_tag if current is not None else None
        next_status = current.status if current is not None else None
        next_is_favorite = current.is_favorite if current is not None else False
        next_rating = current.rating if current is not None else None

        if is_favorite_provided:
            next_is_favorite = bool(is_favorite)
        if rating_provided:
            next_rating = rating

        insert_statement = sqlite_insert(FileUserMeta).values(
            file_id=file_id,
            color_tag=next_color_tag,
            status=next_status,
            rating=next_rating,
            is_favorite=next_is_favorite,
            updated_at=updated_at,
        )
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[FileUserMeta.file_id],
            set_={
                "is_favorite": insert_statement.excluded.is_favorite,
                "rating": insert_statement.excluded.rating,
                "updated_at": insert_statement.excluded.updated_at,
            },
        )
        session.execute(upsert_statement)
        session.flush()
