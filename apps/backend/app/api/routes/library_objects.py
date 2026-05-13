from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.db.session.session import get_db
from app.schemas.library_objects import (
    LibraryObjectDetailResponse,
    LibraryObjectListResponse,
    LibraryObjectMembersResponse,
    LibraryObjectScanRequest,
    LibraryObjectScanResponse,
    LibraryObjectSortBy,
    LibraryOverviewStatsResponse,
    SortOrder,
)
from app.services.library.object_scanner import LibraryObjectScannerService


router = APIRouter(prefix="/library", tags=["library"])
library_object_service = LibraryObjectScannerService()


@router.post("/objects/scan", response_model=LibraryObjectScanResponse)
def scan_library_objects(
    payload: LibraryObjectScanRequest,
    db: Session = Depends(get_db),
) -> LibraryObjectScanResponse:
    return library_object_service.scan_objects(
        db,
        root_path=payload.root_path,
        source_id=payload.source_id,
        dry_run=payload.dry_run,
    )


@router.get("/objects", response_model=LibraryObjectListResponse)
def list_library_objects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    object_type: str | None = Query(default=None),
    needs_review: bool | None = Query(default=None),
    query: str | None = Query(default=None),
    sort_by: LibraryObjectSortBy = Query(default="last_scanned_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> LibraryObjectListResponse:
    return library_object_service.list_objects(
        db,
        page=page,
        page_size=page_size,
        object_type=object_type,
        needs_review=needs_review,
        query=query,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/objects/{object_id}", response_model=LibraryObjectDetailResponse)
def get_library_object(
    object_id: int = Path(..., ge=1),
    members_page: int = Query(default=1, ge=1),
    members_page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> LibraryObjectDetailResponse:
    return library_object_service.get_object_detail(
        db,
        object_id,
        members_page=members_page,
        members_page_size=members_page_size,
    )


@router.get("/objects/{object_id}/members", response_model=LibraryObjectMembersResponse)
def list_library_object_members(
    object_id: int = Path(..., ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    role: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> LibraryObjectMembersResponse:
    return library_object_service.list_members(db, object_id, page=page, page_size=page_size, role=role)


@router.get("/overview", response_model=LibraryOverviewStatsResponse)
def get_library_overview(db: Session = Depends(get_db)) -> LibraryOverviewStatsResponse:
    return library_object_service.overview_stats(db)
