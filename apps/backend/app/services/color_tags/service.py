from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.api.schemas.file import BatchColorTagUpdateResponse, FileColorTagItemResponse, FileColorTagResponse
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.repositories.file.repository import FileRepository
from app.repositories.file_user_meta.repository import FileUserMetaRepository


ALLOWED_COLOR_TAGS = {"red", "yellow", "green", "blue", "purple"}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ColorTagsService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.file_user_meta_repository = FileUserMetaRepository()

    def update_color_tag(self, session: Session, file_id: int, raw_color_tag: str | None) -> FileColorTagResponse:
        file = self.file_repository.get_by_id(session, file_id)
        if file is None:
            raise NotFoundError("FILE_NOT_FOUND", "File not found.")

        normalized_color_tag = self._normalize_color_tag(raw_color_tag)
        updated_at = _utcnow()

        if normalized_color_tag is None:
            self.file_user_meta_repository.clear_color_tag(session, file_id, updated_at)
        else:
            self.file_user_meta_repository.upsert_color_tag(session, file_id, normalized_color_tag, updated_at)

        session.commit()
        persisted_meta = self.file_user_meta_repository.get_by_file_id(session, file_id)
        return FileColorTagResponse(
            item=FileColorTagItemResponse(
                id=file_id,
                color_tag=persisted_meta.color_tag if persisted_meta is not None else None,
            )
        )

    def update_color_tag_for_files(self, session: Session, file_ids: list[int], raw_color_tag: str | None) -> BatchColorTagUpdateResponse:
        deduped_file_ids = list(dict.fromkeys(file_ids))
        if not deduped_file_ids:
            raise BadRequestError("FILE_IDS_INVALID", "At least one file id is required.")

        files = self.file_repository.list_active_files_by_ids(session, deduped_file_ids)
        if len(files) != len(deduped_file_ids):
            raise BadRequestError("BATCH_FILE_SELECTION_INVALID", "One or more selected files are unavailable.")

        normalized_color_tag = self._normalize_color_tag(raw_color_tag)
        updated_at = _utcnow()

        if normalized_color_tag is None:
            self.file_user_meta_repository.clear_color_tag_for_files(session, deduped_file_ids, updated_at)
        else:
            self.file_user_meta_repository.upsert_color_tag_for_files(
                session,
                deduped_file_ids,
                normalized_color_tag,
                updated_at,
            )

        session.commit()
        return BatchColorTagUpdateResponse(
            updated_file_ids=deduped_file_ids,
            updated_count=len(deduped_file_ids),
            color_tag=normalized_color_tag,
        )

    def _normalize_color_tag(self, raw_color_tag: str | None) -> str | None:
        if raw_color_tag is None:
            return None

        normalized = raw_color_tag.strip().lower()
        if not normalized or normalized not in ALLOWED_COLOR_TAGS:
            raise BadRequestError("COLOR_TAG_INVALID", "Color tag is invalid.")
        return normalized
