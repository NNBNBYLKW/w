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
from app.services.library.browse_v2 import browse_v2_service
from app.schemas.browse_v2 import BrowseV2Response


router = APIRouter(tags=["library"])


@router.get("/library/storage-summary")
def storage_summary(db: Session = Depends(get_db)):
    from sqlalchemy import func, select as sa_select
    from app.db.models.file import File as FileModel
    total = db.scalar(sa_select(func.count()).select_from(FileModel)) or 0
    external = db.scalar(sa_select(func.count()).select_from(FileModel).where(FileModel.storage_state == "external")) or 0
    inbox = db.scalar(sa_select(func.count()).select_from(FileModel).where(FileModel.storage_state == "inbox")) or 0
    managed = db.scalar(sa_select(func.count()).select_from(FileModel).where(FileModel.storage_state == "managed")) or 0
    return {
        "total_count": total,
        "external_count": external,
        "inbox_count": inbox,
        "managed_count": managed,
    }
books_library_service = BooksLibraryService()
games_library_service = GamesLibraryService()
media_library_service = MediaLibraryService()
software_library_service = SoftwareLibraryService()


@router.get("/library/books", response_model=BooksListResponse)
def list_books_library(
    tag_id: int | None = Query(default=None, ge=1),
    color_tag: ColorTagValue | None = Query(default=None),
    storage_state: str | None = Query(default=None, pattern="^(external|inbox|managed)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: FileListSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> BooksListResponse:
    params = BooksListQueryParams(
        tag_id=tag_id,
        color_tag=color_tag,
        storage_state=storage_state,
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
    storage_state: str | None = Query(default=None, pattern="^(external|inbox|managed)$"),
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
        storage_state=storage_state,
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
    storage_state: str | None = Query(default=None, pattern="^(external|inbox|managed)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: FileListSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> SoftwareListResponse:
    params = SoftwareListQueryParams(
        tag_id=tag_id,
        color_tag=color_tag,
        storage_state=storage_state,
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
    storage_state: str | None = Query(default=None, pattern="^(external|inbox|managed)$"),
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
        storage_state=storage_state,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return media_library_service.list_media(db, params)


# ── Phase 8A: Browse v2 ─────────────────────────────────

@router.get("/library/browse", response_model=BrowseV2Response)
def browse_v2_cards(
    domain: str = Query(default="media", pattern="^(media|documents|apps|assets)$"),
    category: str | None = Query(default=None),
    storage_state: str = Query(default="all", pattern="^(all|external|inbox|managed)$"),
    card_kind: str = Query(default="all", pattern="^(all|object|loose_file)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="modified_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
) -> BrowseV2Response:
    return browse_v2_service.list_cards(
        db,
        domain=domain,
        category=category or None,
        storage_state=storage_state,
        card_kind=card_kind,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
