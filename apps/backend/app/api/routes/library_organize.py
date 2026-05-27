from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.db.session.session import get_db
from app.schemas.library_organize import (
    ActionUpdateRequest,
    CandidateListResponse,
    CandidateScanResponse,
    CopyFailedActionsResponse,
    ExecutePlanRequest,
    GenerateAssetYamlMergeResponse,
    GenerateRollbackResponse,
    GenerateSuggestionsResponse,
    ExecutePlanResponse,
    GeneratePlanRequest,
    GeneratePlanResponse,
    ManagedComposePlanRequest,
    ManagedComposePlanResponse,
    OrganizeCandidateItem,
    OrganizeStatsResponse,
    OrganizeSuggestionItem,
    OrganizeSuggestionListResponse,
    OrganizeTemplateItem,
    OrganizeTemplateListResponse,
    PlanLogsResponse,
    PlanDetailResponse,
    PlanListResponse,
    PlanUpdateRequest,
    PreflightResponse,
    ReconcilePlanResponse,
)
from app.services.library.organize import organize_service


router = APIRouter(prefix="/library/organize", tags=["library"])


@router.post("/candidates/scan", response_model=CandidateScanResponse)
def scan_candidates(db: Session = Depends(get_db)) -> CandidateScanResponse:
    return organize_service.scan_candidates(db)


@router.get("/candidates", response_model=CandidateListResponse)
def list_candidates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    candidate_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    detected_type: str | None = Query(default=None),
    confidence: str | None = Query(default=None),
    query: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> CandidateListResponse:
    return organize_service.list_candidates(
        db,
        page=page,
        page_size=page_size,
        candidate_type=candidate_type,
        status=status,
        detected_type=detected_type,
        confidence=confidence,
        query=query,
    )


@router.get("/candidates/{candidate_id}", response_model=OrganizeCandidateItem)
def get_candidate(
    candidate_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> OrganizeCandidateItem:
    return organize_service.get_candidate(db, candidate_id)


@router.post("/candidates/{candidate_id}/ignore", response_model=OrganizeCandidateItem)
def ignore_candidate(
    candidate_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> OrganizeCandidateItem:
    return organize_service.ignore_candidate(db, candidate_id)


@router.post("/candidates/{candidate_id}/suggestions/generate", response_model=GenerateSuggestionsResponse)
def generate_candidate_suggestions(
    candidate_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> GenerateSuggestionsResponse:
    return organize_service.generate_candidate_suggestions(db, candidate_id)


@router.get("/candidates/{candidate_id}/suggestions", response_model=OrganizeSuggestionListResponse)
def list_candidate_suggestions(
    candidate_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> OrganizeSuggestionListResponse:
    return organize_service.list_candidate_suggestions(db, candidate_id)


@router.post("/suggestions/{suggestion_id}/accept", response_model=OrganizeSuggestionItem)
def accept_suggestion(
    suggestion_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> OrganizeSuggestionItem:
    return organize_service.accept_suggestion(db, suggestion_id)


@router.post("/suggestions/{suggestion_id}/reject", response_model=OrganizeSuggestionItem)
def reject_suggestion(
    suggestion_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> OrganizeSuggestionItem:
    return organize_service.reject_suggestion(db, suggestion_id)


@router.post("/plans/generate", response_model=GeneratePlanResponse)
def generate_plan(
    payload: GeneratePlanRequest,
    db: Session = Depends(get_db),
) -> GeneratePlanResponse:
    return organize_service.generate_plan(
        db, payload.candidate_ids, payload.strategy, payload.target_library_root_id, payload.template_key
    )


@router.get("/plans", response_model=PlanListResponse)
def list_plans(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    status: str | None = Query(default=None),
    plan_kind: str | None = Query(default=None),
    query: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PlanListResponse:
    return organize_service.list_plans(db, page=page, page_size=page_size, status=status, plan_kind=plan_kind, query=query)


@router.get("/plans/{plan_id}", response_model=PlanDetailResponse)
def get_plan(
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> PlanDetailResponse:
    return organize_service.get_plan_detail(db, plan_id)


@router.post("/plans/{plan_id}/refresh-conflicts", response_model=PlanDetailResponse)
def refresh_plan_conflicts(
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> PlanDetailResponse:
    return organize_service.refresh_plan_conflicts(db, plan_id)


@router.post("/plans/{plan_id}/prepare", response_model=PreflightResponse)
def prepare_plan(
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> PreflightResponse:
    """Atomically mark-ready + preflight. Does NOT execute."""
    return organize_service.prepare_plan(db, plan_id)


@router.post("/plans/{plan_id}/preflight", response_model=PreflightResponse)
def preflight_plan(
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> PreflightResponse:
    return organize_service.preflight_plan(db, plan_id)


@router.post("/plans/{plan_id}/execute", response_model=ExecutePlanResponse)
def execute_plan(
    payload: ExecutePlanRequest,
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ExecutePlanResponse:
    return organize_service.execute_plan(db, plan_id, confirm=payload.confirm)


@router.get("/plans/{plan_id}/logs", response_model=PlanLogsResponse)
def get_plan_logs(
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> PlanLogsResponse:
    return organize_service.list_plan_logs(db, plan_id)


@router.patch("/plans/{plan_id}", response_model=PlanDetailResponse)
def update_plan(
    payload: PlanUpdateRequest,
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> PlanDetailResponse:
    return organize_service.update_plan(db, plan_id, title=payload.title, summary=payload.summary)


@router.patch("/actions/{action_id}", response_model=PlanDetailResponse)
def update_action(
    payload: ActionUpdateRequest,
    action_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> PlanDetailResponse:
    return organize_service.update_action(
        db,
        action_id,
        target_path=payload.target_path,
        payload_json=payload.payload_json,
        status=payload.status,
        reason=payload.reason,
    )


@router.post("/plans/{plan_id}/mark-ready", response_model=PlanDetailResponse)
def mark_ready(
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> PlanDetailResponse:
    return organize_service.mark_ready(db, plan_id)


@router.post("/plans/{plan_id}/cancel", response_model=PlanDetailResponse)
def cancel_plan(
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> PlanDetailResponse:
    return organize_service.cancel_plan(db, plan_id)


@router.post("/plans/{plan_id}/reconcile", response_model=ReconcilePlanResponse)
def reconcile_plan(
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ReconcilePlanResponse:
    return organize_service.reconcile_plan(db, plan_id)


@router.post("/plans/{plan_id}/copy-failed-actions", response_model=CopyFailedActionsResponse)
def copy_failed_actions(
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> CopyFailedActionsResponse:
    return organize_service.copy_failed_actions_to_new_plan(db, plan_id)


@router.post("/plans/{plan_id}/generate-rollback", response_model=GenerateRollbackResponse)
def generate_rollback_plan(
    plan_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> GenerateRollbackResponse:
    return organize_service.generate_rollback_plan(db, plan_id)


@router.post("/actions/{action_id}/generate-asset-yaml-merge", response_model=GenerateAssetYamlMergeResponse)
def generate_asset_yaml_merge_draft(
    action_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> GenerateAssetYamlMergeResponse:
    return organize_service.generate_asset_yaml_merge_draft(db, action_id)


@router.get("/templates", response_model=OrganizeTemplateListResponse)
def list_templates() -> OrganizeTemplateListResponse:
    items = organize_service.get_templates()
    return OrganizeTemplateListResponse(items=[OrganizeTemplateItem(**t) for t in items])


@router.get("/stats", response_model=OrganizeStatsResponse)
def get_organize_stats(db: Session = Depends(get_db)) -> OrganizeStatsResponse:
    return organize_service.organize_stats(db)


# ── Phase 8C-4A: Managed Compose Creation Plan ───────────

@router.post("/plans/managed-compose", response_model=ManagedComposePlanResponse, status_code=201)
def create_managed_compose_plan(
    body: ManagedComposePlanRequest,
    db: Session = Depends(get_db),
) -> ManagedComposePlanResponse:
    try:
        result = organize_service.create_managed_compose_plan(
            db,
            file_ids=body.file_ids,
            object_name=body.object_name,
            object_type=body.object_type,
            target_library_root_id=body.target_library_root_id,
        )
        return ManagedComposePlanResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
