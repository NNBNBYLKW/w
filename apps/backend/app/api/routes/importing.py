from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session.session import get_db
from app.schemas.importing import (
    ConfirmInboxItemRequest,
    ConfirmObjectCandidateRequest,
    GeneratePlanRequest,
    ImportBatchCreateRequest,
    ImportBatchListResponse,
    ImportBatchResponse,
    ComposeExternalRequest,
    ComposeExternalResponse,
    ComposeObjectRequest,
    ComposeObjectResponse,
    ImportFileCollectionRequest,
    ImportFileCollectionResponse,
    ImportFilesRequest,
    ImportFilesResponse,
    ImportFolderRequest,
    ImportFolderResponse,
    InboxItemListResponse,
    InboxItemResponse,
    InboxItemUpdateRequest,
    ObjectCandidateDetailResponse,
    ObjectCandidateListResponse,
    ObjectCandidateResponse,
    ObjectCandidateUpdateRequest,
    PlanGeneratedResponse,
)
from app.services.importing.recovery import recovery_service
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


# ── Inbox Item Review ───────────────────────────────────

@router.patch("/inbox/items/{item_id}", response_model=InboxItemResponse)
def update_inbox_item(
    item_id: int,
    body: InboxItemUpdateRequest,
    db: Session = Depends(get_db),
) -> InboxItemResponse:
    item = import_service.get_inbox_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found.")
    if body.final_object_type is not None:
        item.final_object_type = body.final_object_type
    if body.target_library_root_id is not None:
        item.target_library_root_id = body.target_library_root_id
    db.commit()
    return InboxItemResponse.model_validate(item)


@router.post("/inbox/items/{item_id}/confirm", response_model=InboxItemResponse)
def confirm_inbox_item(
    item_id: int,
    body: ConfirmInboxItemRequest,
    db: Session = Depends(get_db),
) -> InboxItemResponse:
    try:
        item = import_service.confirm_inbox_item(
            db, item_id,
            final_object_type=body.final_object_type,
            target_library_root_id=body.target_library_root_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return InboxItemResponse.model_validate(item)


@router.post("/inbox/items/{item_id}/reject", response_model=InboxItemResponse)
def reject_inbox_item(
    item_id: int,
    db: Session = Depends(get_db),
) -> InboxItemResponse:
    try:
        item = import_service.reject_inbox_item(db, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return InboxItemResponse.model_validate(item)


@router.post("/inbox/items/{item_id}/create-candidate", response_model=dict)
def create_candidate_from_inbox_item(
    item_id: int,
    db: Session = Depends(get_db),
) -> dict:
    try:
        candidate = import_service.create_candidate_from_inbox_item(db, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return {"candidate_id": candidate.id, "inbox_item_id": item_id}


# ── Object Candidate Review ─────────────────────────────

@router.post("/object-candidates/{candidate_id}/confirm", response_model=ObjectCandidateResponse)
def confirm_object_candidate(
    candidate_id: int,
    body: ConfirmObjectCandidateRequest,
    db: Session = Depends(get_db),
) -> ObjectCandidateResponse:
    try:
        oc = import_service.confirm_object_candidate(
            db, candidate_id,
            final_object_type=body.final_object_type,
            launch_file_id=body.launch_file_id,
            target_library_root_id=body.target_library_root_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return ObjectCandidateResponse.model_validate(oc)


@router.post("/object-candidates/{candidate_id}/reject", response_model=ObjectCandidateResponse)
def reject_object_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
) -> ObjectCandidateResponse:
    try:
        oc = import_service.reject_object_candidate(db, candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return ObjectCandidateResponse.model_validate(oc)


@router.post("/object-candidates/{candidate_id}/create-candidate", response_model=dict)
def create_candidate_from_object_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
) -> dict:
    try:
        candidate = import_service.create_candidate_from_object_candidate(db, candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return {
        "candidate_id": candidate.id,
        "import_object_candidate_id": candidate_id,
    }


# ── Generate Draft Plan ─────────────────────────────────

@router.post("/organize-plans", response_model=PlanGeneratedResponse)
def generate_draft_plan(
    body: GeneratePlanRequest,
    db: Session = Depends(get_db),
) -> PlanGeneratedResponse:
    if not body.candidate_ids:
        raise HTTPException(status_code=400, detail="At least one candidate_id is required.")
    try:
        plan = import_service.generate_draft_plan_from_candidates(
            db, candidate_ids=body.candidate_ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return PlanGeneratedResponse(
        plan_id=plan.id,
        status=plan.status,
        actions_count=0,
        blocked_count=0,
        warning_count=0,
    )


# ── Recovery ────────────────────────────────────────────

@router.post("/recovery/scan")
def run_recovery_scan(db: Session = Depends(get_db)):
    summary = recovery_service.scan(db)
    return {
        "orphan_inbox_count": summary.orphan_inbox_count,
        "missing_inbox_count": summary.missing_inbox_count,
        "missing_managed_count": summary.missing_managed_count,
        "failed_import_count": summary.failed_import_count,
        "incomplete_batch_count": summary.incomplete_batch_count,
        "incomplete_journal_count": summary.incomplete_journal_count,
        "high_count": summary.high_count,
        "warning_count": summary.warning_count,
        "info_count": summary.info_count,
    }


@router.get("/recovery/summary")
def get_recovery_summary(db: Session = Depends(get_db)):
    summary = recovery_service.scan(db)
    return {
        "orphan_inbox_count": summary.orphan_inbox_count,
        "missing_inbox_count": summary.missing_inbox_count,
        "missing_managed_count": summary.missing_managed_count,
        "failed_import_count": summary.failed_import_count,
        "incomplete_batch_count": summary.incomplete_batch_count,
        "incomplete_journal_count": summary.incomplete_journal_count,
        "high_count": summary.high_count,
        "warning_count": summary.warning_count,
        "info_count": summary.info_count,
    }


@router.get("/recovery/findings")
def list_recovery_findings(
    severity: str | None = Query(default=None),
    finding_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    summary = recovery_service.scan(db)
    findings = summary.findings
    if severity:
        findings = [f for f in findings if f["severity"] == severity]
    if finding_type:
        findings = [f for f in findings if f["finding_type"] == finding_type]
    total = len(findings)
    offset = (page - 1) * page_size
    return {
        "items": findings[offset:offset + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/recovery/findings/persisted")
def list_persisted_findings(
    severity: str | None = Query(default=None),
    scan_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    from sqlalchemy import text as sa_text
    where = []
    params: dict = {}
    if severity:
        where.append("severity = :severity")
        params["severity"] = severity
    if scan_id:
        where.append("scan_id = :scan_id")
        params["scan_id"] = scan_id
    where_clause = (" AND " + " AND ".join(where)) if where else ""
    total_row = db.execute(
        sa_text(f"SELECT COUNT(*) FROM recovery_findings{where_clause}"), params
    ).fetchone()
    total = total_row[0] if total_row else 0
    offset = (page - 1) * page_size
    rows = db.execute(
        sa_text(
            f"SELECT scan_id, scanned_at, finding_type, severity, entity_type, entity_id, path, message, suggested_action "
            f"FROM recovery_findings{where_clause} ORDER BY scanned_at DESC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": page_size, "offset": offset},
    ).fetchall()
    return {
        "items": [dict(r._mapping) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ── Retry Failed Import ─────────────────────────────────

@router.post("/inbox/items/{item_id}/retry")
def retry_failed_import(item_id: int, db: Session = Depends(get_db)):
    item = import_service.get_inbox_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found.")
    if item.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed imports can be retried.")

    source = item.source_path
    if not source or not __import__("pathlib").Path(source).exists():
        raise HTTPException(status_code=400, detail="Source file no longer exists. Cannot retry import.")

    try:
        target_root = import_service._resolve_inbox_root(db)
        managed_source = import_service._get_managed_source(db)
        # get batch
        batch_id = item.import_batch_id
        inbox_dir = import_service._ensure_inbox_dir(target_root.root_path, batch_id)
        op_id = str(__import__("uuid").uuid4())

        result = import_service._copy_one_file(
            db, import_service.repository.get_batch(db, batch_id),
            source, inbox_dir,
            managed_source.id, target_root.id, op_id,
        )
        if result.file_id and result.inbox_item_id:
            import_service.repository.update_inbox_item_status(db, item, "imported")
            # update file reference on the item
            item.file_id = result.file_id
            item.inbox_path = result.inbox_path
            item.error_message = None

            import_service.repository.append_journal_entry(
                db, operation_id=op_id, operation_type="retry_import",
                entity_type="inbox_item", entity_id=item.id,
                status="succeeded",
                after_json=__import__("json").dumps({"new_inbox_path": result.inbox_path}),
            )
        db.commit()
        return {"status": "ok", "inbox_item_id": item.id, "inbox_path": result.inbox_path}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Phase 7H-3: Multi-file Collection Import ──────────────

@router.post("/file-collections", response_model=ImportFileCollectionResponse, status_code=201)
def import_file_collection(
    body: ImportFileCollectionRequest,
    db: Session = Depends(get_db),
) -> ImportFileCollectionResponse:
    try:
        result = import_service.import_file_collection(
            db,
            paths=body.paths,
            collection_name=body.collection_name,
            suggested_object_type=body.suggested_object_type,
            target_library_root_id=body.target_library_root_id,
        )
        return ImportFileCollectionResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Phase 8C-1: Compose inbox loose items ───────────────

@router.post("/compose", response_model=ComposeObjectResponse, status_code=201)
def compose_inbox_items(
    body: ComposeObjectRequest,
    db: Session = Depends(get_db),
) -> ComposeObjectResponse:
    try:
        result = import_service.compose_inbox_items(
            db,
            inbox_item_ids=body.inbox_item_ids,
            object_name=body.object_name,
            suggested_object_type=body.suggested_object_type,
            target_library_root_id=body.target_library_root_id,
        )
        return ComposeObjectResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Phase 8C-3: Compose external files ──────────────────

@router.post("/compose/external-files", response_model=ComposeExternalResponse, status_code=201)
def compose_external_files(
    body: ComposeExternalRequest,
    db: Session = Depends(get_db),
) -> ComposeExternalResponse:
    try:
        result = import_service.compose_external_files(
            db,
            file_ids=body.file_ids,
            object_name=body.object_name,
            suggested_object_type=body.suggested_object_type,
            target_library_root_id=body.target_library_root_id,
        )
        return ComposeExternalResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
