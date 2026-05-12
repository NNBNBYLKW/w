from sqlalchemy.orm import Session

from app.core.classification import PLACEMENT_BOOKS, effective_placement
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.api.schemas.search import LibraryPlacementFilter, SearchQueryParams, SearchResponse, SearchResultItemResponse
from app.repositories.file.repository import FileRepository
from app.repositories.file_user_meta.repository import FileUserMetaRepository
from app.repositories.tag.repository import TagRepository


ALLOWED_COLOR_TAGS = {"red", "yellow", "green", "blue", "purple"}


class SearchService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()
        self.file_user_meta_repository = FileUserMetaRepository()
        self.tag_repository = TagRepository()

    def search_files(self, session: Session, params: SearchQueryParams) -> SearchResponse:
        if params.tag_id is not None and self.tag_repository.get_by_id(session, params.tag_id) is None:
            raise NotFoundError("TAG_NOT_FOUND", "Tag not found.")

        normalized_color_tag = self._normalize_color_tag(params.color_tag)
        normalized_library_placement = self._normalize_library_placement(params.library_placement)
        files, total = self.file_repository.search_indexed_files(
            session,
            query=params.query,
            file_type=params.file_type,
            file_kind=None,
            library_placement=normalized_library_placement,
            tag_id=params.tag_id,
            color_tag=normalized_color_tag,
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        items = [
            self._to_search_item(session, file)
            for file in files
        ]
        return SearchResponse(
            items=items,
            page=params.page,
            page_size=params.page_size,
            total=total,
        )

    def _to_search_item(self, session: Session, file) -> SearchResultItemResponse:
        file_user_meta = self.file_user_meta_repository.get_by_file_id(session, file.id)
        manual_placement = file_user_meta.manual_placement if file_user_meta is not None else None
        return SearchResultItemResponse(
            id=file.id,
            name=file.name,
            path=file.path,
            file_type=file.file_type,
            file_kind=file.file_kind,
            auto_placement=file.auto_placement,
            manual_placement=manual_placement,
            effective_placement=effective_placement(file.auto_placement, manual_placement),
            modified_at=file.modified_at_fs or file.discovered_at,
        )

    def _normalize_color_tag(self, raw_color_tag: str | None) -> str | None:
        if raw_color_tag is None:
            return None

        normalized = raw_color_tag.strip().lower()
        if not normalized or normalized not in ALLOWED_COLOR_TAGS:
            raise BadRequestError("COLOR_TAG_INVALID", "Color tag is invalid.")
        return normalized

    def _normalize_library_placement(self, raw_placement: LibraryPlacementFilter | None) -> str | None:
        if raw_placement is None:
            return None
        if raw_placement == "documents":
            return PLACEMENT_BOOKS
        return raw_placement
