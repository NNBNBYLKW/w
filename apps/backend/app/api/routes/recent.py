from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.file import SortOrder
from app.api.schemas.recent import RecentListQueryParams, RecentListResponse
from app.db.session.session import get_db
from app.services.recent.service import RecentImportsService


router = APIRouter(tags=["recent"])
recent_imports_service = RecentImportsService()


@router.get("/recent", response_model=RecentListResponse)
def list_recent_imports(
    range: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> RecentListResponse:
    params = RecentListQueryParams(
        range=range,
        page=page,
        page_size=page_size,
        sort_order=sort_order,
    )
    return recent_imports_service.list_recent_imports(db, params)
