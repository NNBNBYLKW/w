from sqlalchemy.orm import Session

from app.api.schemas.file import FileListItemResponse, FileListQueryParams, FileListResponse
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.repositories.file.repository import FileRepository
from app.repositories.source.repository import SourceRepository
from app.repositories.tag.repository import TagRepository


ALLOWED_COLOR_TAGS = {"red", "yellow", "green", "blue", "purple"}


class FilesService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.source_repository = SourceRepository()
        self.tag_repository = TagRepository()

    def list_files(self, session: Session, params: FileListQueryParams) -> FileListResponse:
        if params.parent_path is not None and params.source_id is None:
            raise BadRequestError(
                "PARENT_PATH_REQUIRES_SOURCE",
                "parent_path requires source_id.",
            )

        if params.source_id is not None:
            source = self.source_repository.get_by_id(session, params.source_id)
            if source is None:
                raise NotFoundError("SOURCE_NOT_FOUND", "Source not found.")

        if params.tag_id is not None and self.tag_repository.get_by_id(session, params.tag_id) is None:
            raise NotFoundError("TAG_NOT_FOUND", "Tag not found.")

        normalized_color_tag = self._normalize_color_tag(params.color_tag)

        files, total = self.file_repository.list_indexed_files(
            session,
            source_id=params.source_id,
            parent_path=params.parent_path,
            tag_id=params.tag_id,
            color_tag=normalized_color_tag,
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        items = [
            FileListItemResponse(
                id=file.id,
                name=file.name,
                path=file.path,
                file_type=file.file_type,
                modified_at=file.modified_at_fs or file.discovered_at,
                size_bytes=file.size_bytes,
            )
            for file in files
        ]
        return FileListResponse(
            items=items,
            page=params.page,
            page_size=params.page_size,
            total=total,
        )

    def _normalize_color_tag(self, raw_color_tag: str | None) -> str | None:
        if raw_color_tag is None:
            return None

        normalized = raw_color_tag.strip().lower()
        if not normalized or normalized not in ALLOWED_COLOR_TAGS:
            raise BadRequestError("COLOR_TAG_INVALID", "Color tag is invalid.")
        return normalized
