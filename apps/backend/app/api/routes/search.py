from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.search import (
    FileTypeFilter,
    SearchQueryParams,
    SearchResponse,
    SearchSortBy,
    SortOrder,
)
from app.db.session.session import get_db
from app.services.search.service import SearchService


router = APIRouter(tags=["search"])
search_service = SearchService()


@router.get("/search", response_model=SearchResponse)
def search_files(
    query: str | None = Query(default=None),
    file_type: FileTypeFilter | None = Query(default=None),
    tag_id: int | None = Query(default=None, ge=1),
    color_tag: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: SearchSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> SearchResponse:
    params = SearchQueryParams(
        query=query,
        file_type=file_type,
        tag_id=tag_id,
        color_tag=color_tag,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return search_service.search_files(db, params)
