from sqlalchemy.orm import Session

from app.api.schemas.search import SearchQueryParams, SearchResponse, SearchResultItemResponse
from app.repositories.file.repository import FileRepository


class SearchService:
    def __init__(self) -> None:
        self.file_repository = FileRepository()

    def search_files(self, session: Session, params: SearchQueryParams) -> SearchResponse:
        files, total = self.file_repository.search_indexed_files(
            session,
            query=params.query,
            file_type=params.file_type,
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
