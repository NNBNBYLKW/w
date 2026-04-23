from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.api.schemas.file import FileStatusItemResponse, FileStatusResponse
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.repositories.file.repository import FileRepository
from app.repositories.file_user_meta.repository import FileUserMetaRepository


ALLOWED_FILE_STATUSES = {"playing", "completed", "shelved"}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class FileStatusService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.file_user_meta_repository = FileUserMetaRepository()

    def update_status(self, session: Session, file_id: int, raw_status: str | None) -> FileStatusResponse:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")

        normalized_status = self._normalize_status(raw_status)
        updated_at = _utcnow()

        if normalized_status is None:
            self.file_user_meta_repository.clear_status(session, file_id, updated_at)
        else:
            self.file_user_meta_repository.upsert_status(session, file_id, normalized_status, updated_at)

        session.commit()
        persisted_meta = self.file_user_meta_repository.get_by_file_id(session, file_id)
        return FileStatusResponse(
            item=FileStatusItemResponse(
                id=file_id,
                status=persisted_meta.status if persisted_meta is not None else None,
            )
        )

    def _normalize_status(self, raw_status: str | None) -> str | None:
        if raw_status is None:
            return None

        normalized = raw_status.strip().lower()
        if not normalized:
            return None
        if normalized not in ALLOWED_FILE_STATUSES:
            raise BadRequestError("FILE_STATUS_INVALID", "File status is invalid.")
        return normalized
