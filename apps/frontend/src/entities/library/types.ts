export type LibraryObjectSortBy = "last_scanned_at" | "updated_at" | "title" | "object_type" | "root_path";
export type LibraryObjectSortOrder = "asc" | "desc";

export type LibraryObjectListQueryInput = {
  page: number;
  page_size: number;
  object_type?: string;
  needs_review?: boolean;
  query?: string;
  sort_by: LibraryObjectSortBy;
  sort_order: LibraryObjectSortOrder;
};

export type LibraryObjectScanInput = {
  root_path?: string;
  source_id?: number;
  dry_run?: boolean;
};

export type LibraryObjectScanResponseVM = {
  scanned_roots: number;
  objects_found: number;
  objects_created: number;
  objects_updated: number;
  needs_review: number;
  errors: string[];
};

export type LibraryObjectListItemVM = {
  id: number;
  object_type: string;
  type_prefix: string;
  title: string | null;
  display_title: string;
  year: number | null;
  tags: string[];
  root_path: string;
  cover_path: string | null;
  primary_file_path: string | null;
  metadata_source: string;
  needs_review: boolean;
  review_reason: string | null;
  last_scanned_at: string;
  members_count: number;
};

export type LibraryObjectListResponseVM = {
  items: LibraryObjectListItemVM[];
  total: number;
  page: number;
  page_size: number;
};

export type AssetMetadataSummaryVM = {
  yaml_path: string | null;
  schema_version: number | null;
  parse_status: string;
  parse_error: string | null;
};

export type LibraryObjectMemberItemVM = {
  id: number;
  object_id: number;
  file_id: number | null;
  relative_path: string;
  absolute_path: string;
  member_role: string;
  sort_index: number | null;
  hidden_from_global: boolean;
  extension: string | null;
  size_bytes: number | null;
  modified_at: string | null;
};

export type LibraryObjectDetailResponseVM = {
  object: LibraryObjectListItemVM;
  asset_metadata: AssetMetadataSummaryVM | null;
  members: LibraryObjectMemberItemVM[];
  members_total: number;
  members_page: number;
  members_page_size: number;
};

export type LibraryObjectMembersResponseVM = {
  items: LibraryObjectMemberItemVM[];
  total: number;
  page: number;
  page_size: number;
};

export type LibraryOverviewStatsResponseVM = {
  total_objects: number;
  needs_review_count: number;
  object_type_counts: Record<string, number>;
  asset_yaml_ok_count: number;
  asset_yaml_invalid_count: number;
  unknown_object_count: number;
  last_object_scan_at: string | null;
};

export type OrganizeCandidateStatus = "pending" | "added_to_plan" | "ignored" | "resolved";

export type OrganizeCandidateListQueryInput = {
  page: number;
  page_size: number;
  candidate_type?: string;
  status?: string;
  detected_type?: string;
  confidence?: string;
  query?: string;
};

export type OrganizeCandidateItemVM = {
  id: number;
  candidate_type: string;
  source_kind: string;
  source_file_id: number | null;
  source_object_id: number | null;
  source_path: string;
  display_name: string;
  detected_type: string;
  confidence: string;
  reason: string;
  status: string;
  ignored_at: string | null;
  created_at: string;
  updated_at: string;
};

export type OrganizeCandidateListResponseVM = {
  items: OrganizeCandidateItemVM[];
  total: number;
  page: number;
  page_size: number;
};

export type CandidateScanResponseVM = {
  scanned_count: number;
  candidates_created: number;
  candidates_updated: number;
  needs_review_count: number;
  ignored_count: number;
};

export type GeneratePlanResponseVM = {
  plan_id: number;
  status: string;
  actions_count: number;
  blocked_count: number;
  warning_count: number;
  target_library_root_id: number | null;
  target_root_path: string | null;
};

export type OrganizePlanListQueryInput = {
  page: number;
  page_size: number;
  status?: string;
  plan_kind?: string;
  query?: string;
};

export type OrganizePlanItemVM = {
  id: number;
  title: string;
  status: string;
  plan_kind: string;
  summary: string | null;
  summary_json: string | null;
  created_at: string;
  updated_at: string;
  confirmed_at: string | null;
  executed_at: string | null;
  execution_started_at: string | null;
  execution_finished_at: string | null;
  execution_summary_json: string | null;
  target_library_root_id: number | null;
  target_root_path: string | null;
  actions_count: number;
  blocked_count: number;
  warning_count: number;
  failed_count: number;
  skipped_count: number;
  reconcile_status: string | null;
  reconciled_at: string | null;
  reconcile_summary_json: string | null;
  parent_plan_id: number | null;
  plan_origin: string | null;
  template_key: string | null;
};

export type OrganizePlanListResponseVM = {
  items: OrganizePlanItemVM[];
  total: number;
  page: number;
  page_size: number;
};

export type OrganizeActionItemVM = {
  id: number;
  plan_id: number;
  action_order: number;
  action_type: string;
  source_path: string | null;
  target_path: string | null;
  payload_json: string | null;
  status: string;
  conflict_status: string;
  conflict_message: string | null;
  reason: string | null;
  before_path: string | null;
  after_path: string | null;
  executed_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  reconcile_status: string | null;
  created_at: string;
  updated_at: string;
};

export type OrganizePlanDetailResponseVM = {
  plan: OrganizePlanItemVM;
  candidates: OrganizeCandidateItemVM[];
  actions: OrganizeActionItemVM[];
};

export type OrganizeStatsResponseVM = {
  pending_candidates: number;
  draft_plans: number;
  ready_plans: number;
  blocked_actions: number;
};

export type OrganizeActionLogItemVM = {
  id: number;
  plan_id: number;
  action_id: number | null;
  event_type: string;
  message: string;
  path_before: string | null;
  path_after: string | null;
  error_message: string | null;
  created_at: string;
};

export type PlanLogsResponseVM = {
  items: OrganizeActionLogItemVM[];
};

export type PreflightResponseVM = {
  plan_id: number;
  can_execute: boolean;
  blocked_count: number;
  warning_count: number;
  actions: OrganizeActionItemVM[];
  messages: string[];
};

export type ExecutePlanResponseVM = {
  plan_id: number;
  status: string;
  affected_source_ids: number[];
  affected_library_root_ids: number[];
};

export type LibraryRootVM = {
  id: number;
  root_path: string;
  display_name: string | null;
  root_kind: "managed";
  is_enabled: boolean;
  is_default: boolean;
  scan_policy: string;
  created_at: string;
  updated_at: string;
};

export type CreateLibraryRootInput = {
  root_path: string;
  display_name?: string;
};

export type UpdateLibraryRootInput = {
  display_name?: string;
  is_enabled?: boolean;
  scan_policy?: string;
};

export type ReconcileActionItemVM = {
  action_id: number;
  action_type: string;
  source_path: string | null;
  target_path: string | null;
  reconcile_status: string;
};

export type ReconcilePlanResponseVM = {
  plan_id: number;
  reconcile_status: string;
  reconciled_at: string;
  summary: Record<string, number>;
  actions: ReconcileActionItemVM[];
};

export type CopyFailedActionsResponseVM = {
  source_plan_id: number;
  new_plan_id: number;
  copied_actions_count: number;
  skipped_actions_count: number;
  plan_origin: string;
};

export type RollbackBlockedActionItemVM = {
  source_action_id: number;
  reason: string;
};

export type GenerateRollbackResponseVM = {
  source_plan_id: number;
  rollback_plan_id: number;
  rollback_actions_count: number;
  blocked_actions_count: number;
  plan_origin: string;
  blocked_actions: RollbackBlockedActionItemVM[];
};

export type FieldDiffItemVM = {
  field: string;
  status: string;
  current: string | null;
  proposed: string | null;
  merged: string | null;
};

export type GenerateAssetYamlMergeResponseVM = {
  source_plan_id: number;
  source_action_id: number;
  merge_plan_id: number;
  backup_action_id: number;
  update_action_id: number;
  plan_origin: string;
  field_diff: FieldDiffItemVM[];
};

export type OrganizeTemplateItemVM = {
  template_key: string;
  object_type: string;
  name: string;
  description: string;
  path_template: string;
  filename_template: string | null;
  is_builtin: boolean;
  is_enabled: boolean;
};

export type OrganizeTemplateListResponseVM = {
  items: OrganizeTemplateItemVM[];
};

export type OrganizeSuggestionTypeVM = "object_type" | "title" | "tags" | "asset_yaml" | "template_key";
export type OrganizeSuggestionStatusVM = "pending" | "accepted" | "rejected" | "expired";

export type OrganizeSuggestionItemVM = {
  id: number;
  candidate_id: number | null;
  plan_id: number | null;
  action_id: number | null;
  suggestion_type: OrganizeSuggestionTypeVM;
  payload_json: string;
  confidence: number | null;
  reason: string | null;
  provider: string;
  status: OrganizeSuggestionStatusVM;
  created_at: string;
  accepted_at: string | null;
  rejected_at: string | null;
};

export type OrganizeSuggestionListResponseVM = {
  items: OrganizeSuggestionItemVM[];
};

export type GenerateSuggestionsResponseVM = {
  candidate_id: number;
  created_count: number;
  items: OrganizeSuggestionItemVM[];
};
