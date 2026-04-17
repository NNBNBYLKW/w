from datetime import datetime

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models.file_metadata import FileMetadata


class FileMetadataRepository:
    def get_by_file_id(self, session: Session, file_id: int) -> FileMetadata | None:
        return session.get(FileMetadata, file_id)

    def upsert_metadata(
        self,
        session: Session,
        file_id: int,
        *,
        width: int | None,
        height: int | None,
        duration_ms: int | None,
        page_count: int | None,
        updated_at: datetime,
    ) -> None:
        insert_statement = sqlite_insert(FileMetadata).values(
            file_id=file_id,
            width=width,
            height=height,
            duration_ms=duration_ms,
            page_count=page_count,
            title=None,
            author=None,
            series=None,
            codec_info=None,
            extra_json=None,
            updated_at=updated_at,
        )
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[FileMetadata.file_id],
            set_={
                "width": insert_statement.excluded.width,
                "height": insert_statement.excluded.height,
                "duration_ms": insert_statement.excluded.duration_ms,
                "page_count": insert_statement.excluded.page_count,
                "updated_at": insert_statement.excluded.updated_at,
            },
        )
        session.execute(upsert_statement)
        session.flush()
