from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.file import FileListSortBy, SortOrder
from app.api.schemas.media import MediaListQueryParams, MediaListResponse, MediaViewScope
from app.db.session.session import get_db
from app.services.media.service import MediaLibraryService


router = APIRouter(tags=["library"])
media_library_service = MediaLibraryService()


@router.get("/library/media", response_model=MediaListResponse)
def list_media_library(
    view_scope: MediaViewScope = Query(default="all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: FileListSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> MediaListResponse:
    params = MediaListQueryParams(
        view_scope=view_scope,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return media_library_service.list_media(db, params)
