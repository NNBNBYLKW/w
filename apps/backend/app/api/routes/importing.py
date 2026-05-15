from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session.session import get_db
from app.schemas.importing import (
    ImportBatchCreateRequest,
    ImportBatchListResponse,
    ImportBatchResponse,
    ImportFilesRequest,
    ImportFilesResponse,
    ImportFolderRequest,
    ImportFolderResponse,
    InboxItemListResponse,
    InboxItemResponse,
    ObjectCandidateDetailResponse,
    ObjectCandidateListResponse,
    ObjectCandidateResponse,
    ObjectCandidateUpdateRequest,
)
from app.services.importing.service import import_service


router = APIRouter(prefix="/library/import", tags=["library"])


# ── Import Batches ──────────────────────────────────────

@router.post("/batches", response_model=ImportBatchResponse, status_code=201)
def create_import_batch(
    body: ImportBatchCreateRequest,
    db: Session = Depends(get_db),
) -> ImportBatchResponse:
    if body.import_method != "copy":
        raise HTTPException(
            status_code=400,
            detail="Only 'copy' import method is supported in Phase 7B. "
            "Move, delete_original, and cleanup_source are not allowed.",
        )
    try:
        batch = import_service.create_import_batch(
            db, source_kind="file_selection", import_method=body.import_method
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return ImportBatchResponse.model_validate(batch)


@router.get("/batches", response_model=ImportBatchListResponse)
def list_import_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ImportBatchListResponse:
    items, total = import_service.list_import_batches(
        db, page=page, page_size=page_size
    )
    return ImportBatchListResponse(
        items=[ImportBatchResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/batches/{batch_id}", response_model=ImportBatchResponse)
def get_import_batch(
    batch_id: int,
    db: Session = Depends(get_db),
) -> ImportBatchResponse:
    batch = import_service.get_import_batch(db, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import batch not found.")
    return ImportBatchResponse.model_validate(batch)


@router.post("/batches/{batch_id}/files", response_model=ImportFilesResponse)
def import_files_to_batch(
    batch_id: int,
    body: ImportFilesRequest,
    db: Session = Depends(get_db),
) -> ImportFilesResponse:
    if not body.paths:
        raise HTTPException(status_code=400, detail="At least one file path is required.")
    try:
        result = import_service.import_files_to_batch(
            db, batch_id=batch_id, paths=body.paths
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


# ── Inbox Items ─────────────────────────────────────────

@router.get("/inbox/items", response_model=InboxItemListResponse)
def list_inbox_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    batch_id: int | None = Query(None),
    db: Session = Depends(get_db),
) -> InboxItemListResponse:
    items, total = import_service.list_inbox_items(
        db, page=page, page_size=page_size, status=status, batch_id=batch_id
    )
    return InboxItemListResponse(
        items=[InboxItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/inbox/items/{item_id}", response_model=InboxItemResponse)
def get_inbox_item(
    item_id: int,
    db: Session = Depends(get_db),
) -> InboxItemResponse:
    item = import_service.get_inbox_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found.")
    return InboxItemResponse.model_validate(item)


# ── Folder Import ────────────────────────────────────────

@router.post("/batches/{batch_id}/folders", response_model=dict)
def import_folder_to_batch(
    batch_id: int,
    body: ImportFolderRequest,
    db: Session = Depends(get_db),
) -> dict:
    if not body.paths:
        raise HTTPException(status_code=400, detail="At least one folder path is required.")
    if body.mode not in {"object", "loose_files"}:
        raise HTTPException(
            status_code=400,
            detail="Mode must be 'object' or 'loose_files'.",
        )
    results: list[dict] = []
    errors: list[dict] = []
    for folder_path in body.paths:
        try:
            result = import_service.import_folder_to_batch(
                db, batch_id=batch_id, folder_path=folder_path, mode=body.mode
            )
            results.append(result)
        except Exception as exc:
            errors.append({"path": folder_path, "error": str(exc)})
    db.commit()
    return {
        "batch_id": batch_id,
        "object_candidates": [r for r in results if "object_candidate_id" in r],
        "created_items": [r for r in results if r.get("mode") == "loose_files"],
        "failed_items": errors,
    }


# ── Object Candidates ────────────────────────────────────

@router.get("/object-candidates", response_model=ObjectCandidateListResponse)
def list_object_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ObjectCandidateListResponse:
    items, total = import_service.list_object_candidates(
        db, page=page, page_size=page_size
    )
    return ObjectCandidateListResponse(
        items=[ObjectCandidateResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/object-candidates/{candidate_id}", response_model=ObjectCandidateDetailResponse)
def get_object_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
) -> ObjectCandidateDetailResponse:
    detail = import_service.get_object_candidate_with_members(db, candidate_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Object candidate not found.")
    return ObjectCandidateDetailResponse(**detail)


@router.patch("/object-candidates/{candidate_id}", response_model=ObjectCandidateResponse)
def update_object_candidate(
    candidate_id: int,
    body: ObjectCandidateUpdateRequest,
    db: Session = Depends(get_db),
) -> ObjectCandidateResponse:
    candidate = import_service.get_object_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Object candidate not found.")
    if candidate.status in {"organized", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="Cannot update an organized or rejected object candidate.",
        )
    if body.final_object_type is not None:
        candidate.final_object_type = body.final_object_type
    if body.launch_file_id is not None:
        # validate launch_file_id belongs to a member
        members = import_service.repository.list_object_members(db, candidate_id)
        member_file_ids = {
            import_service.repository.get_inbox_item(db, m.inbox_item_id).file_id
            for m in members
            if import_service.repository.get_inbox_item(db, m.inbox_item_id)
        }
        if body.launch_file_id not in member_file_ids:
            raise HTTPException(
                status_code=400,
                detail="launch_file_id must belong to a member of this object candidate.",
            )
        candidate.launch_file_id = body.launch_file_id
    db.commit()
    return ObjectCandidateResponse.model_validate(candidate)
