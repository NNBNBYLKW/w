from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


CandidateStatus = Literal["pending", "added_to_plan", "ignored", "resolved"]
PlanStatus = Literal["draft", "ready", "cancelled", "executing", "completed", "completed_with_errors", "failed"]
ActionStatus = Literal["draft", "ready", "blocked", "cancelled", "executing", "succeeded", "failed", "skipped"]
ConflictStatus = Literal["ok", "warning", "blocked", "stale", "unchecked"]
PlanReconcileStatus = Literal["not_required", "pending", "reconciled", "reconcile_failed"]
ActionReconcileStatus = Literal[
    "not_checked", "matched", "source_still_exists", "target_missing",
    "both_exist", "both_missing", "target_not_directory", "asset_yaml_missing", "unknown",
]
SuggestionType = Literal["object_type", "title", "tags", "asset_yaml", "template_key"]
SuggestionStatus = Literal["pending", "accepted", "rejected", "expired"]


class OrganizeTemplateItem(BaseModel):
    template_key: str
    object_type: str
    name: str
    description: str
    path_template: str
    filename_template: str | None = None
    is_builtin: bool = True
    is_enabled: bool = True


class OrganizeTemplateListResponse(BaseModel):
    items: list[OrganizeTemplateItem]


class OrganizeSuggestionItem(BaseModel):
    id: int
    candidate_id: int | None = None
    plan_id: int | None = None
    action_id: int | None = None
    suggestion_type: SuggestionType
    payload_json: str
    confidence: float | None = None
    reason: str | None = None
    provider: str
    status: SuggestionStatus
    created_at: datetime
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None


class OrganizeSuggestionListResponse(BaseModel):
    items: list[OrganizeSuggestionItem]


class GenerateSuggestionsResponse(BaseModel):
    candidate_id: int
    created_count: int
    items: list[OrganizeSuggestionItem]


class CandidateScanResponse(BaseModel):
    scanned_count: int
    candidates_created: int
    candidates_updated: int
    needs_review_count: int
    ignored_count: int


class OrganizeCandidateItem(BaseModel):
    id: int
    candidate_type: str
    source_kind: str
    source_file_id: int | None
    source_object_id: int | None
    source_path: str
    display_name: str
    detected_type: str
    confidence: str
    reason: str
    status: str
    ignored_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CandidateListResponse(BaseModel):
    items: list[OrganizeCandidateItem]
    total: int
    page: int
    page_size: int


class GeneratePlanRequest(BaseModel):
    candidate_ids: list[int] = Field(min_length=1)
    strategy: str | None = "default"
    target_library_root_id: int | None = None
    template_key: str | None = None


class GeneratePlanResponse(BaseModel):
    plan_id: int
    status: str
    actions_count: int
    blocked_count: int
    warning_count: int
    target_library_root_id: int | None = None
    target_root_path: str | None = None


class OrganizeActionItem(BaseModel):
    id: int
    plan_id: int
    action_order: int
    action_type: str
    source_path: str | None
    target_path: str | None
    payload_json: str | None
    status: str
    conflict_status: str
    conflict_message: str | None
    reason: str | None
    before_path: str | None = None
    after_path: str | None = None
    executed_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    reconcile_status: ActionReconcileStatus | None = None
    created_at: datetime
    updated_at: datetime


class OrganizePlanItem(BaseModel):
    id: int
    title: str
    status: str
    plan_kind: str
    summary: str | None
    summary_json: str | None
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None
    executed_at: datetime | None
    execution_started_at: datetime | None = None
    execution_finished_at: datetime | None = None
    execution_summary_json: str | None = None
    actions_count: int = 0
    blocked_count: int = 0
    warning_count: int = 0
    target_library_root_id: int | None = None
    target_root_path: str | None = None
    failed_count: int = 0
    skipped_count: int = 0
    reconcile_status: PlanReconcileStatus | None = None
    reconciled_at: datetime | None = None
    reconcile_summary_json: str | None = None
    parent_plan_id: int | None = None
    plan_origin: str | None = None
    template_key: str | None = None


class PlanListResponse(BaseModel):
    items: list[OrganizePlanItem]
    total: int
    page: int
    page_size: int


class PlanDetailResponse(BaseModel):
    plan: OrganizePlanItem
    candidates: list[OrganizeCandidateItem]
    actions: list[OrganizeActionItem]


class PlanUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None


class ActionUpdateRequest(BaseModel):
    target_path: str | None = None
    payload_json: str | None = None
    status: Literal["draft", "cancelled"] | None = None
    reason: str | None = None


class OrganizeStatsResponse(BaseModel):
    pending_candidates: int
    draft_plans: int
    ready_plans: int
    blocked_actions: int


class OrganizeActionLogItem(BaseModel):
    id: int
    plan_id: int
    action_id: int | None
    event_type: str
    message: str
    path_before: str | None
    path_after: str | None
    error_message: str | None
    created_at: datetime


class PlanLogsResponse(BaseModel):
    items: list[OrganizeActionLogItem]


class PreflightResponse(BaseModel):
    plan_id: int
    can_execute: bool
    blocked_count: int
    warning_count: int
    actions: list[OrganizeActionItem]
    messages: list[str]


class ExecutePlanRequest(BaseModel):
    confirm: bool = False


class ExecutePlanResponse(BaseModel):
    plan_id: int
    status: str
    affected_source_ids: list[int] = []
    affected_library_root_ids: list[int] = []


class ReconcileActionItem(BaseModel):
    action_id: int
    action_type: str
    source_path: str | None = None
    target_path: str | None = None
    reconcile_status: str


class ReconcilePlanResponse(BaseModel):
    plan_id: int
    reconcile_status: str
    reconciled_at: datetime
    summary: dict[str, int]
    actions: list[ReconcileActionItem]


class CopyFailedActionsResponse(BaseModel):
    source_plan_id: int
    new_plan_id: int
    copied_actions_count: int
    skipped_actions_count: int
    plan_origin: str


class RollbackBlockedActionItem(BaseModel):
    source_action_id: int
    reason: str


class GenerateRollbackResponse(BaseModel):
    source_plan_id: int
    rollback_plan_id: int
    rollback_actions_count: int
    blocked_actions_count: int
    plan_origin: str
    blocked_actions: list[RollbackBlockedActionItem]


class FieldDiffItem(BaseModel):
    field: str
    status: str
    current: str | None = None
    proposed: str | None = None
    merged: str | None = None


class GenerateAssetYamlMergeResponse(BaseModel):
    source_plan_id: int
    source_action_id: int
    merge_plan_id: int
    backup_action_id: int
    update_action_id: int
    plan_origin: str
    field_diff: list[FieldDiffItem]


# ── Phase 8C-4A: Managed Compose Creation Plan ──────────

class ManagedComposePlanMember(BaseModel):
    file_id: int
    role: str
    relative_path: str
    source_path: str | None = None
    target_path: str | None = None


class ManagedComposePlanRequest(BaseModel):
    file_ids: list[int] = Field(min_length=1)
    object_name: str
    object_type: str
    target_library_root_id: int | None = None


class ManagedComposePlanResponse(BaseModel):
    plan_id: int
    status: str
    plan_kind: str
    actions_count: int
    target_library_root_id: int | None = None
    target_root_path: str | None = None
    target_object_dir: str
    planned_members: list[ManagedComposePlanMember] = []
    notes: list[str] = []


# ── Phase 8D-A2: Object Amendment Draft Plan ────────────

class AmendmentPlannedAction(BaseModel):
    action_type: str
    source_path: str | None = None
    target_path: str | None = None
    file_id: int | None = None
    member_role: str | None = None
    amendment_action: str | None = None


class AmendmentPlanRequest(BaseModel):
    add_file_ids: list[int] = []
    remove_member_ids: list[int] = []
    target_library_root_id: int | None = None
    remove_target_policy: str = "managed_loose_area"


class AmendmentPlanResponse(BaseModel):
    plan_id: int
    plan_kind: str = "object_amendment"
    object_id: int
    amendment_type: str
    status: str
    add_count: int
    remove_count: int
    planned_actions: list[AmendmentPlannedAction] = []
    notes: list[str] = []
