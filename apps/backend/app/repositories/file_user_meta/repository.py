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

    def clear_color_tag(self, session: Session, file_id: int, updated_at: datetime) -> int:
        statement = (
            update(FileUserMeta)
            .where(FileUserMeta.file_id == file_id)
            .values(color_tag=None, updated_at=updated_at)
        )
        result = session.execute(statement)
        session.flush()
        return int(result.rowcount or 0)
