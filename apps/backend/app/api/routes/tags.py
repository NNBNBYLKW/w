from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.api.schemas.file import FileListResponse, FileListSortBy, SortOrder
from app.api.schemas.tag import TagCreateRequest, TagFileListQueryParams, TagListResponse, TagResponse
from app.db.session.session import get_db
from app.services.tags.service import TagsService


router = APIRouter(tags=["tags"])
tags_service = TagsService()


@router.get("/tags", response_model=TagListResponse)
def list_tags(db: Session = Depends(get_db)) -> TagListResponse:
    return tags_service.list_tags(db)


@router.post("/tags", response_model=TagResponse)
def create_tag(
    payload: TagCreateRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TagResponse:
    tag_response, created = tags_service.create_tag(db, payload)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return tag_response


@router.get("/tags/{tag_id}/files", response_model=FileListResponse)
def list_tag_files(
    tag_id: int = Path(..., ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: FileListSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> FileListResponse:
    params = TagFileListQueryParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return tags_service.list_files_for_tag(db, tag_id, params)
