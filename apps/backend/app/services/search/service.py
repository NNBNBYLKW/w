from sqlalchemy.orm import Session

from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.api.schemas.search import SearchQueryParams, SearchResponse, SearchResultItemResponse
from app.repositories.file.repository import FileRepository
from app.repositories.tag.repository import TagRepository


ALLOWED_COLOR_TAGS = {"red", "yellow", "green", "blue", "purple"}


class SearchService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.tag_repository = TagRepository()

    def search_files(self, session: Session, params: SearchQueryParams) -> SearchResponse:
        if params.tag_id is not None and self.tag_repository.get_by_id(session, params.tag_id) is None:
            raise NotFoundError("TAG_NOT_FOUND", "Tag not found.")

        normalized_color_tag = self._normalize_color_tag(params.color_tag)
        files, total = self.file_repository.search_indexed_files(
            session,
            query=params.query,
            file_type=params.file_type,
            tag_id=params.tag_id,
            color_tag=normalized_color_tag,
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        items = [
            SearchResultItemResponse(
                id=file.id,
                name=file.name,
                path=file.path,
                file_type=file.file_type,
                modified_at=file.modified_at_fs or file.discovered_at,
            )
            for file in files
        ]
        return SearchResponse(
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
