import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas.file import (
    BatchColorTagUpdateRequest,
    BatchColorTagUpdateResponse,
    BatchMetaUpdateRequest,
    BatchMetaUpdateResponse,
    BatchPlacementUpdateRequest,
    BatchPlacementUpdateResponse,
    BatchTagAttachRequest,
    BatchTagAttachResponse,
    ColorTagUpdateRequest,
    FileColorTagResponse,
    FileDetailResponse,
    FileListQueryParams,
    FileListResponse,
    FileListSortBy,
    FilePlacementResponse,
    FilePlacementUpdateRequest,
    FileStatusResponse,
    FileStatusUpdateRequest,
    ThumbnailWarmupRequest,
    ThumbnailWarmupResponse,
    FileUserMetaPatchRequest,
    FileUserMetaResponse,
    FileVideoPreviewResponse,
    SortOrder,
)
from app.api.schemas.tag import TagCreateRequest, TagListResponse
from app.core.errors.exceptions import BadRequestError, NotFoundError
from app.core.time import utcnow
from app.db.models.file import File
from app.db.models.game_session import GameSession
from app.db.session.session import get_db
from app.services.color_tags.service import ColorTagsService
from app.services.details.service import DetailsService
from app.services.file_status.service import FileStatusService
from app.services.files.service import FilesService
from app.services.file_user_meta.service import FileUserMetaService
from app.services.tags.service import TagsService
from app.services.thumbnails.service import ThumbnailService
from app.services.classification.suggester import RuleBasedSuggester
from app.workers.epub.parser import EpubParser
from app.db.models.trash_entry import TrashEntry
from datetime import datetime, timedelta


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


@router.patch("/files/batch/placement", response_model=BatchPlacementUpdateResponse)
def update_placement_batch(
    payload: BatchPlacementUpdateRequest,
    db: Session = Depends(get_db),
) -> BatchPlacementUpdateResponse:
    return file_user_meta_service.update_files_placement(db, payload)


@router.post("/files/batch/meta", response_model=BatchMetaUpdateResponse)
def batch_update_meta(
    payload: BatchMetaUpdateRequest,
    db: Session = Depends(get_db),
) -> BatchMetaUpdateResponse:
    return file_user_meta_service.batch_update(db, payload)


@router.get("/files", response_model=FileListResponse)
def list_files(
    source_id: int | None = Query(default=None, ge=1),
    parent_path: str | None = Query(default=None),
    file_kind: str | None = Query(default=None),
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
        file_kind=file_kind,
        tag_id=tag_id,
        color_tag=color_tag,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return files_service.list_files(db, params)


@router.get("/files/{file_id}/siblings")
def get_sibling_files(
    file_id: int = Path(..., ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    file = files_service.get_file(db, file_id)
    parent = os.path.dirname(file.path) if file else ""
    siblings = files_service.list_files_in_directory(db, parent, file_id, limit)
    return {"items": siblings}


@router.get("/files/{file_id}", response_model=FileDetailResponse)
def get_file_details(
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> FileDetailResponse:
    return details_service.get_file_details(db, file_id)


@router.post("/files/thumbnails/warmup", response_model=ThumbnailWarmupResponse)
def warmup_file_thumbnails(
    payload: ThumbnailWarmupRequest,
    db: Session = Depends(get_db),
) -> ThumbnailWarmupResponse:
    return ThumbnailWarmupResponse(**thumbnail_service.warmup_thumbnails(db, payload.file_ids).__dict__)


@router.get("/files/duplicates")
def list_duplicates(min_size: int = 0, db: Session = Depends(get_db)):
    rows = db.execute(
        select(File.checksum_hint, func.count(File.id).label("cnt"))
        .where(File.checksum_hint.isnot(None), File.file_kind != "other", File.size_bytes >= min_size)
        .group_by(File.checksum_hint)
        .having(func.count(File.id) > 1)
    ).fetchall()
    groups = []
    for ch, cnt in rows:
        files = db.execute(select(File).where(File.checksum_hint == ch)).scalars().all()
        groups.append({"checksum": ch, "count": cnt, "files": [{"id": f.id, "name": f.name, "path": f.path, "size_bytes": f.size_bytes} for f in files]})
    return {"items": groups}


@router.get("/debug/thumbnails/warmup")
def thumbnail_warmup_diagnostics() -> dict:
    return thumbnail_service.get_warmup_debug_snapshot()


@router.get("/debug/thumbnails/warmup/{file_id}")
def thumbnail_warmup_file_diagnostics(
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> dict:
    return thumbnail_service.get_warmup_debug_for_file(db, file_id)


@router.get("/files/{file_id}/poster")
def get_file_video_poster(
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> FileResponse:
    poster = thumbnail_service.get_video_poster(db, file_id)
    return FileResponse(
        path=poster.path,
        media_type=poster.media_type,
        headers={"Cache-Control": "no-store"},
    )


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


@router.get("/files/{file_id}/stream")
def get_file_stream(
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    file = files_service.get_file(db, file_id)
    if not os.path.isfile(file.path):
        raise BadRequestError("FILE_NOT_FOUND_ON_DISK", "File not found on disk.")
    media_type = file.mime_type or "application/octet-stream"
    return StreamingResponse(
        open(file.path, "rb"),
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
        },
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


@router.patch("/files/{file_id}/placement", response_model=FilePlacementResponse)
def update_file_placement(
    payload: FilePlacementUpdateRequest,
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> FilePlacementResponse:
    return file_user_meta_service.update_file_placement(db, file_id, payload.manual_placement)


@router.get("/files/{file_id}/epub-content")
def get_epub_content(file_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    file = files_service.get_file(db, file_id)
    if not file.path.lower().endswith(".epub"):
        raise BadRequestError("FILE_NOT_EPUB", "File is not an EPUB")
    parsed = EpubParser().parse(file.path)
    return {"item": parsed}


@router.post("/files/classify-suggestions")
def get_suggestions(payload: dict, db: Session = Depends(get_db)):
    file_ids = payload.get("file_ids", [])
    suggester = RuleBasedSuggester()
    results = []
    for fid in file_ids:
        f = files_service.get_file(db, fid)
        suggestions = suggester.suggest(f.name, f.path)
        results.append({"file_id": fid, "name": f.name, "suggestions": suggestions})
    return {"items": results}


@router.post("/files/{file_id}/sessions")
def start_game_session(
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    session = GameSession(file_id=file_id, started_at=utcnow())
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id}


@router.patch("/files/{file_id}/sessions/{session_id}")
def end_game_session(
    file_id: int = Path(..., ge=1),
    session_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, session_id)
    if not session:
        raise NotFoundError("SESSION_NOT_FOUND", "Session not found")
    session.ended_at = utcnow()
    session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())
    db.commit()
    return {"item": {"id": session.id, "duration_seconds": session.duration_seconds}}


@router.post("/files/{file_id}/trash")
def trash_file(
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    file = files_service.get_file(db, file_id)
    if file is None:
        raise NotFoundError("FILE_NOT_FOUND", "File not found.")

    existing = db.query(TrashEntry).filter(TrashEntry.file_id == file_id).first()
    if existing:
        raise BadRequestError("ALREADY_TRASHED", "File is already in trash.")

    now = utcnow()
    trash_entry = TrashEntry(
        file_id=file_id,
        original_path=file.path,
        trashed_at=now,
        expires_at=now + timedelta(days=30),
    )
    file.is_deleted = True
    file.updated_at = now
    db.add(trash_entry)
    db.commit()
    return {
        "item": {
            "id": trash_entry.id,
            "file_id": file_id,
            "original_path": file.path,
            "trashed_at": trash_entry.trashed_at.isoformat(),
            "expires_at": trash_entry.expires_at.isoformat(),
        }
    }


@router.post("/files/{file_id}/restore")
def restore_file(
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    trash_entry = db.query(TrashEntry).filter(TrashEntry.file_id == file_id).first()
    if trash_entry is None:
        raise NotFoundError("NOT_IN_TRASH", "File is not in trash.")

    file = files_service.get_file(db, file_id)
    if file is not None:
        file.is_deleted = False
        file.updated_at = utcnow()

    db.delete(trash_entry)
    db.commit()
    return {"item": {"file_id": file_id, "status": "restored"}}


@router.get("/trash")
def list_trash(
    db: Session = Depends(get_db),
):
    entries = db.query(TrashEntry).order_by(TrashEntry.trashed_at.desc()).all()
    return {
        "items": [
            {
                "id": e.id,
                "file_id": e.file_id,
                "original_path": e.original_path,
                "trashed_at": e.trashed_at.isoformat(),
                "expires_at": e.expires_at.isoformat(),
            }
            for e in entries
        ]
    }
