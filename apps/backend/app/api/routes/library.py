from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.books import BooksListQueryParams, BooksListResponse
from app.api.schemas.file import ColorTagValue, FileListSortBy, FileStatusValue, SortOrder
from app.api.schemas.games import GamesListQueryParams, GamesListResponse
from app.api.schemas.media import MediaListQueryParams, MediaListResponse, MediaViewScope
from app.api.schemas.software import SoftwareListQueryParams, SoftwareListResponse
from app.db.session.session import get_db
from app.services.books.service import BooksLibraryService
from app.services.games.service import GamesLibraryService
from app.services.media.service import MediaLibraryService
from app.services.software.service import SoftwareLibraryService


router = APIRouter(tags=["library"])
books_library_service = BooksLibraryService()
games_library_service = GamesLibraryService()
media_library_service = MediaLibraryService()
software_library_service = SoftwareLibraryService()


@router.get("/library/books", response_model=BooksListResponse)
def list_books_library(
    tag_id: int | None = Query(default=None, ge=1),
    color_tag: ColorTagValue | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: FileListSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> BooksListResponse:
    params = BooksListQueryParams(
        tag_id=tag_id,
        color_tag=color_tag,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return books_library_service.list_books(db, params)


@router.get("/library/games", response_model=GamesListResponse)
def list_games_library(
    status: FileStatusValue | None = Query(default=None),
    tag_id: int | None = Query(default=None, ge=1),
    color_tag: ColorTagValue | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: FileListSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> GamesListResponse:
    params = GamesListQueryParams(
        status=status,
        tag_id=tag_id,
        color_tag=color_tag,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return games_library_service.list_games(db, params)


@router.get("/library/software", response_model=SoftwareListResponse)
def list_software_library(
    tag_id: int | None = Query(default=None, ge=1),
    color_tag: ColorTagValue | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: FileListSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> SoftwareListResponse:
    params = SoftwareListQueryParams(
        tag_id=tag_id,
        color_tag=color_tag,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return software_library_service.list_software(db, params)


@router.get("/library/media", response_model=MediaListResponse)
def list_media_library(
    view_scope: MediaViewScope = Query(default="all"),
    tag_id: int | None = Query(default=None, ge=1),
    color_tag: ColorTagValue | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: FileListSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> MediaListResponse:
    params = MediaListQueryParams(
        view_scope=view_scope,
        tag_id=tag_id,
        color_tag=color_tag,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return media_library_service.list_media(db, params)
