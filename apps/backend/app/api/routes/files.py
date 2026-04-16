from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.schemas.file import (
    ColorTagUpdateRequest,
    FileColorTagResponse,
    FileDetailResponse,
    FileListQueryParams,
    FileListResponse,
    FileListSortBy,
    SortOrder,
)
from app.api.schemas.tag import TagCreateRequest, TagListResponse
from app.db.session.session import get_db
from app.services.color_tags.service import ColorTagsService
from app.services.details.service import DetailsService
from app.services.files.service import FilesService
from app.services.tags.service import TagsService


router = APIRouter(tags=["files"])
details_service = DetailsService()
files_service = FilesService()
tags_service = TagsService()
color_tags_service = ColorTagsService()


@router.get("/files", response_model=FileListResponse)
def list_files(
    source_id: int | None = Query(default=None, ge=1),
    parent_path: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: FileListSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> FileListResponse:
    params = FileListQueryParams(
        source_id=source_id,
        parent_path=parent_path,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return files_service.list_files(db, params)


@router.get("/files/{file_id}", response_model=FileDetailResponse)
def get_file_details(
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> FileDetailResponse:
    return details_service.get_file_details(db, file_id)


@router.post("/files/{file_id}/tags", response_model=TagListResponse)
def attach_tag_to_file(
    payload: TagCreateRequest,
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> TagListResponse:
    return tags_service.attach_tag_to_file(db, file_id, payload)


@router.delete("/files/{file_id}/tags/{tag_id}", response_model=TagListResponse)
def remove_tag_from_file(
    file_id: int = Path(..., ge=1),
    tag_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> TagListResponse:
    return tags_service.remove_tag_from_file(db, file_id, tag_id)


@router.patch("/files/{file_id}/color-tag", response_model=FileColorTagResponse)
def update_color_tag(
    payload: ColorTagUpdateRequest,
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> FileColorTagResponse:
    return color_tags_service.update_color_tag(db, file_id, payload.color_tag)
