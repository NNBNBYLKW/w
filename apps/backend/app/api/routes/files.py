from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.schemas.file import (
    BatchColorTagUpdateRequest,
    BatchColorTagUpdateResponse,
    BatchTagAttachRequest,
    BatchTagAttachResponse,
    ColorTagUpdateRequest,
    FileColorTagResponse,
    FileDetailResponse,
    FileListQueryParams,
    FileListResponse,
    FileListSortBy,
    FileStatusResponse,
    FileStatusUpdateRequest,
    FileUserMetaPatchRequest,
    FileUserMetaResponse,
    FileVideoPreviewResponse,
    SortOrder,
)
from app.api.schemas.tag import TagCreateRequest, TagListResponse
from app.db.session.session import get_db
from app.services.color_tags.service import ColorTagsService
from app.services.details.service import DetailsService
from app.services.file_status.service import FileStatusService
from app.services.files.service import FilesService
from app.services.file_user_meta.service import FileUserMetaService
from app.services.tags.service import TagsService
from app.services.thumbnails.service import ThumbnailService


router = APIRouter(tags=["files"])
details_service = DetailsService()
files_service = FilesService()
tags_service = TagsService()
color_tags_service = ColorTagsService()
file_status_service = FileStatusService()
file_user_meta_service = FileUserMetaService()
thumbnail_service = ThumbnailService()


@router.post("/files/batch/tags", response_model=BatchTagAttachResponse)
def attach_tag_to_files_batch(
    payload: BatchTagAttachRequest,
    db: Session = Depends(get_db),
) -> BatchTagAttachResponse:
    return tags_service.attach_tag_to_files(db, payload)


@router.patch("/files/batch/color-tag", response_model=BatchColorTagUpdateResponse)
def update_color_tag_batch(
    payload: BatchColorTagUpdateRequest,
    db: Session = Depends(get_db),
) -> BatchColorTagUpdateResponse:
    return color_tags_service.update_color_tag_for_files(db, payload.file_ids, payload.color_tag)


@router.get("/files", response_model=FileListResponse)
def list_files(
    source_id: int | None = Query(default=None, ge=1),
    parent_path: str | None = Query(default=None),
    tag_id: int | None = Query(default=None, ge=1),
    color_tag: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: FileListSortBy = Query(default="modified_at"),
    sort_order: SortOrder = Query(default="desc"),
    db: Session = Depends(get_db),
) -> FileListResponse:
    params = FileListQueryParams(
        source_id=source_id,
        parent_path=parent_path,
        tag_id=tag_id,
        color_tag=color_tag,
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


@router.get("/files/{file_id}/thumbnail")
def get_file_thumbnail(
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> FileResponse:
    thumbnail = thumbnail_service.get_thumbnail(db, file_id)
    return FileResponse(
        path=thumbnail.path,
        media_type=thumbnail.media_type,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/files/{file_id}/video-preview", response_model=FileVideoPreviewResponse)
def get_file_video_preview(
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> FileVideoPreviewResponse:
    return FileVideoPreviewResponse(item=thumbnail_service.get_video_preview(db, file_id))


@router.get("/files/{file_id}/video-preview/frames/{frame_index}")
def get_file_video_preview_frame(
    file_id: int = Path(..., ge=1),
    frame_index: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> FileResponse:
    frame_path = thumbnail_service.get_video_preview_frame_path(db, file_id, frame_index)
    return FileResponse(
        path=frame_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


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


@router.patch("/files/{file_id}/status", response_model=FileStatusResponse)
def update_file_status(
    payload: FileStatusUpdateRequest,
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> FileStatusResponse:
    return file_status_service.update_status(db, file_id, payload.status)


@router.patch("/files/{file_id}/user-meta", response_model=FileUserMetaResponse)
def update_file_user_meta(
    payload: FileUserMetaPatchRequest,
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> FileUserMetaResponse:
    return file_user_meta_service.update_user_meta(db, file_id, payload)
