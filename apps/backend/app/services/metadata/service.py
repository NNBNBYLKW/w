from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.file import File
from app.repositories.file_metadata.repository import FileMetadataRepository
from app.workers.metadata.extractor import MetadataExtractorWorker


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MetadataService:
    def __init__(self) -> None:
        self.file_metadata_repository = FileMetadataRepository()
        self.extractor = MetadataExtractorWorker()

    def enrich_scanned_files(self, session: Session, files: list[File]) -> None:
        for file in files:
            try:
                metadata = self.extractor.extract_for_file(file)
            except Exception as error:
                if self.extractor.is_expected_extraction_failure(error):
                    continue
                continue

            if metadata is None:
                continue

            if not self._has_any_active_value(metadata.width, metadata.height):
                continue

            try:
                with session.begin_nested():
                    self.file_metadata_repository.upsert_metadata(
                        session,
                        file.id,
                        width=metadata.width,
                        height=metadata.height,
                        duration_ms=metadata.duration_ms,
                        page_count=metadata.page_count,
                        updated_at=_utcnow(),
                    )
            except SQLAlchemyError:
                continue

    def _has_any_active_value(self, width: int | None, height: int | None) -> bool:
        return width is not None or height is not None
