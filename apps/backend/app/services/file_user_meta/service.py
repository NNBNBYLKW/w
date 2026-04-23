from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.api.schemas.file import FileUserMetaPatchRequest, FileUserMetaResponse
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.repositories.file.repository import FileRepository
from app.repositories.file_user_meta.repository import FileUserMetaRepository


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class FileUserMetaService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.file_user_meta_repository = FileUserMetaRepository()

    def update_user_meta(
        self,
        session: Session,
        file_id: int,
        payload: FileUserMetaPatchRequest,
    ) -> FileUserMetaResponse:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")

        fields_set = payload.model_fields_set
        is_favorite_provided = "is_favorite" in fields_set
        rating_provided = "rating" in fields_set

        if not is_favorite_provided and not rating_provided:
            raise BadRequestError("FILE_USER_META_PATCH_EMPTY", "No file user metadata fields were provided.")

        if is_favorite_provided and not isinstance(payload.is_favorite, bool):
            raise BadRequestError("FILE_FAVORITE_INVALID", "Favorite must be true or false.")

        if rating_provided and not self._is_valid_rating(payload.rating):
            raise BadRequestError("FILE_RATING_INVALID", "Rating must be an integer from 1 to 5, or null.")

        self.file_user_meta_repository.update_user_meta(
            session,
            file_id,
            is_favorite_provided=is_favorite_provided,
            is_favorite=payload.is_favorite if is_favorite_provided else None,
            rating_provided=rating_provided,
            rating=payload.rating if rating_provided else None,
            updated_at=_utcnow(),
        )
        session.commit()

        persisted = self.file_user_meta_repository.get_by_file_id(session, file_id)
        return FileUserMetaResponse(
            item={
                "id": file_id,
                "is_favorite": persisted.is_favorite if persisted is not None else False,
                "rating": persisted.rating if persisted is not None else None,
            }
        )

    def _is_valid_rating(self, value: object) -> bool:
        if value is None:
            return True
        if isinstance(value, bool) or not isinstance(value, int):
            return False
        return 1 <= value <= 5
