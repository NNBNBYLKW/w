from app.core.time import utcnow

from sqlalchemy.orm import Session

from app.api.schemas.file import (
    BatchPlacementUpdateRequest,
    BatchPlacementUpdateResponse,
    FilePlacementResponse,
    FileUserMetaPatchRequest,
    FileUserMetaResponse,
)
from app.core.classification import MANUAL_PLACEMENT_VALUES, effective_placement
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.repositories.file.repository import FileRepository
from app.repositories.file_user_meta.repository import FileUserMetaRepository


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
            updated_at=utcnow(),
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

    def update_file_placement(
        self,
        session: Session,
        file_id: int,
        manual_placement: str | None,
    ) -> FilePlacementResponse:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")
        self._ensure_valid_manual_placement(manual_placement)

        updated_at = utcnow()
        self.file_user_meta_repository.upsert_manual_placement(
            session,
            file_id,
            manual_placement,
            updated_at,
        )
        session.commit()

        persisted = self.file_user_meta_repository.get_by_file_id(session, file_id)
        persisted_manual_placement = persisted.manual_placement if persisted is not None else None
        return FilePlacementResponse(
            item={
                "id": file_id,
                "file_kind": file.file_kind,
                "auto_placement": file.auto_placement,
                "manual_placement": persisted_manual_placement,
                "effective_placement": effective_placement(file.auto_placement, persisted_manual_placement),
            }
        )

    def update_files_placement(
        self,
        session: Session,
        payload: BatchPlacementUpdateRequest,
    ) -> BatchPlacementUpdateResponse:
        self._ensure_valid_manual_placement(payload.manual_placement)
        deduped_file_ids = list(dict.fromkeys(payload.file_ids))
        files = self.file_repository.list_active_files_by_ids(session, deduped_file_ids)
        found_ids = {file.id for file in files}
        if len(found_ids) != len(deduped_file_ids):
            raise BadRequestError("BATCH_FILE_SELECTION_INVALID", "All selected files must exist and be active.")

        updated_at = utcnow()
        self.file_user_meta_repository.upsert_manual_placement_for_files(
            session,
            deduped_file_ids,
            payload.manual_placement,
            updated_at,
        )
        session.commit()
        return BatchPlacementUpdateResponse(
            updated_file_ids=deduped_file_ids,
            updated_count=len(deduped_file_ids),
            manual_placement=payload.manual_placement,
        )

    def _ensure_valid_manual_placement(self, value: str | None) -> None:
        if value is not None and value not in MANUAL_PLACEMENT_VALUES:
            raise BadRequestError("FILE_PLACEMENT_INVALID", "Library placement is invalid.")

    def _is_valid_rating(self, value: object) -> bool:
        if value is None:
            return True
        if isinstance(value, bool) or not isinstance(value, int):
            return False
        return 1 <= value <= 5
