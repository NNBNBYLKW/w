import { getApiBaseUrl, parseResponse } from "./client";
import type {
  CreateLibraryRootInput,
  LibraryObjectDetailResponseVM,
  LibraryObjectListQueryInput,
  LibraryObjectListResponseVM,
  LibraryObjectMembersResponseVM,
  LibraryObjectScanInput,
  LibraryObjectScanResponseVM,
  LibraryOverviewStatsResponseVM,
  LibraryRootVM,
  CandidateScanResponseVM,
  ExecutePlanResponseVM,
  GeneratePlanResponseVM,
  GenerateRollbackResponseVM,
  GenerateSuggestionsResponseVM,
  OrganizeCandidateItemVM,
  OrganizeCandidateListQueryInput,
  OrganizeCandidateListResponseVM,
  OrganizePlanDetailResponseVM,
  OrganizePlanListQueryInput,
  OrganizePlanListResponseVM,
  OrganizeStatsResponseVM,
  OrganizeSuggestionItemVM,
  OrganizeSuggestionListResponseVM,
  PlanLogsResponseVM,
  PreflightResponseVM,
  CopyFailedActionsResponseVM,
  GenerateAssetYamlMergeResponseVM,
  OrganizeTemplateListResponseVM,
  ReconcilePlanResponseVM,
  UpdateLibraryRootInput,
} from "../../entities/library/types";


export async function scanLibraryObjects(input: LibraryObjectScanInput = {}): Promise<LibraryObjectScanResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/objects/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<LibraryObjectScanResponseVM>(response);
}


export async function listLibraryObjects(input: LibraryObjectListQueryInput): Promise<LibraryObjectListResponseVM> {
  const params = new URLSearchParams();
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  params.set("sort_by", input.sort_by);
  params.set("sort_order", input.sort_order);
  if (input.object_type) params.set("object_type", input.object_type);
  if (input.needs_review !== undefined) params.set("needs_review", String(input.needs_review));
  if (input.query?.trim()) params.set("query", input.query.trim());
  const response = await fetch(`${getApiBaseUrl()}/library/objects?${params.toString()}`);
  return parseResponse<LibraryObjectListResponseVM>(response);
}


export async function getLibraryObject(objectId: number): Promise<LibraryObjectDetailResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/objects/${objectId}?members_page=1&members_page_size=50`);
  return parseResponse<LibraryObjectDetailResponseVM>(response);
}


export async function listLibraryObjectMembers(input: {
  objectId: number;
  page: number;
  page_size: number;
  role?: string;
}): Promise<LibraryObjectMembersResponseVM> {
  const params = new URLSearchParams();
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  if (input.role) params.set("role", input.role);
  const response = await fetch(`${getApiBaseUrl()}/library/objects/${input.objectId}/members?${params.toString()}`);
  return parseResponse<LibraryObjectMembersResponseVM>(response);
}


export async function getLibraryOverview(): Promise<LibraryOverviewStatsResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/overview`);
  return parseResponse<LibraryOverviewStatsResponseVM>(response);
}


export async function scanOrganizeCandidates(): Promise<CandidateScanResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/candidates/scan`, { method: "POST" });
  return parseResponse<CandidateScanResponseVM>(response);
}


export async function listOrganizeCandidates(input: OrganizeCandidateListQueryInput): Promise<OrganizeCandidateListResponseVM> {
  const params = new URLSearchParams();
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  if (input.candidate_type) params.set("candidate_type", input.candidate_type);
  if (input.status) params.set("status", input.status);
  if (input.detected_type) params.set("detected_type", input.detected_type);
  if (input.confidence) params.set("confidence", input.confidence);
  if (input.query?.trim()) params.set("query", input.query.trim());
  const response = await fetch(`${getApiBaseUrl()}/library/organize/candidates?${params.toString()}`);
  return parseResponse<OrganizeCandidateListResponseVM>(response);
}


export async function getOrganizeCandidate(candidateId: number): Promise<OrganizeCandidateItemVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/candidates/${candidateId}`);
  return parseResponse<OrganizeCandidateItemVM>(response);
}


export async function ignoreOrganizeCandidate(candidateId: number): Promise<OrganizeCandidateItemVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/candidates/${candidateId}/ignore`, { method: "POST" });
  return parseResponse<OrganizeCandidateItemVM>(response);
}


export async function generateOrganizeSuggestions(candidateId: number): Promise<GenerateSuggestionsResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/candidates/${candidateId}/suggestions/generate`, { method: "POST" });
  return parseResponse<GenerateSuggestionsResponseVM>(response);
}


export async function listOrganizeSuggestions(candidateId: number): Promise<OrganizeSuggestionListResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/candidates/${candidateId}/suggestions`);
  return parseResponse<OrganizeSuggestionListResponseVM>(response);
}


export async function acceptOrganizeSuggestion(suggestionId: number): Promise<OrganizeSuggestionItemVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/suggestions/${suggestionId}/accept`, { method: "POST" });
  return parseResponse<OrganizeSuggestionItemVM>(response);
}


export async function rejectOrganizeSuggestion(suggestionId: number): Promise<OrganizeSuggestionItemVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/suggestions/${suggestionId}/reject`, { method: "POST" });
  return parseResponse<OrganizeSuggestionItemVM>(response);
}


export async function generateOrganizePlan(
  candidateIds: number[],
  targetLibraryRootId?: number,
  templateKey?: string,
): Promise<GeneratePlanResponseVM> {
  const body: Record<string, unknown> = { candidate_ids: candidateIds, strategy: "default" };
  if (targetLibraryRootId !== undefined) body.target_library_root_id = targetLibraryRootId;
  if (templateKey) body.template_key = templateKey;
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseResponse<GeneratePlanResponseVM>(response);
}


export async function listOrganizePlans(input: OrganizePlanListQueryInput): Promise<OrganizePlanListResponseVM> {
  const params = new URLSearchParams();
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  if (input.status) params.set("status", input.status);
  if (input.plan_kind) params.set("plan_kind", input.plan_kind);
  if (input.query?.trim()) params.set("query", input.query.trim());
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans?${params.toString()}`);
  return parseResponse<OrganizePlanListResponseVM>(response);
}


export async function getOrganizePlan(planId: number): Promise<OrganizePlanDetailResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans/${planId}`);
  return parseResponse<OrganizePlanDetailResponseVM>(response);
}


export async function updateOrganizePlan(planId: number, input: { title?: string; summary?: string }): Promise<OrganizePlanDetailResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans/${planId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<OrganizePlanDetailResponseVM>(response);
}


export async function updateOrganizeAction(
  actionId: number,
  input: { target_path?: string; payload_json?: string; status?: "draft" | "cancelled"; reason?: string },
): Promise<OrganizePlanDetailResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/actions/${actionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<OrganizePlanDetailResponseVM>(response);
}


export async function markOrganizePlanReady(planId: number): Promise<OrganizePlanDetailResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans/${planId}/mark-ready`, { method: "POST" });
  return parseResponse<OrganizePlanDetailResponseVM>(response);
}


export async function preflightOrganizePlan(planId: number): Promise<PreflightResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans/${planId}/preflight`, { method: "POST" });
  return parseResponse<PreflightResponseVM>(response);
}


export async function executeOrganizePlan(planId: number): Promise<ExecutePlanResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans/${planId}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm: true }),
  });
  return parseResponse<ExecutePlanResponseVM>(response);
}


export async function getOrganizePlanLogs(planId: number): Promise<PlanLogsResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans/${planId}/logs`);
  return parseResponse<PlanLogsResponseVM>(response);
}


export async function cancelOrganizePlan(planId: number): Promise<OrganizePlanDetailResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans/${planId}/cancel`, { method: "POST" });
  return parseResponse<OrganizePlanDetailResponseVM>(response);
}


export async function getOrganizeStats(): Promise<OrganizeStatsResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/stats`);
  return parseResponse<OrganizeStatsResponseVM>(response);
}

// Library Roots

export async function listLibraryRoots(): Promise<LibraryRootVM[]> {
  const response = await fetch(`${getApiBaseUrl()}/library/roots`);
  const data = await parseResponse<{ items: LibraryRootVM[] }>(response);
  return data.items;
}

export async function createLibraryRoot(input: CreateLibraryRootInput): Promise<LibraryRootVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/roots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<LibraryRootVM>(response);
}

export async function updateLibraryRoot(rootId: number, input: UpdateLibraryRootInput): Promise<LibraryRootVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/roots/${rootId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<LibraryRootVM>(response);
}

export async function setDefaultLibraryRoot(rootId: number): Promise<LibraryRootVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/roots/${rootId}/set-default`, { method: "POST" });
  return parseResponse<LibraryRootVM>(response);
}

export async function reconcileOrganizePlan(planId: number): Promise<ReconcilePlanResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans/${planId}/reconcile`, { method: "POST" });
  return parseResponse<ReconcilePlanResponseVM>(response);
}

export async function copyFailedActions(planId: number): Promise<CopyFailedActionsResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans/${planId}/copy-failed-actions`, { method: "POST" });
  return parseResponse<CopyFailedActionsResponseVM>(response);
}

export async function generateRollbackPlan(planId: number): Promise<GenerateRollbackResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/plans/${planId}/generate-rollback`, { method: "POST" });
  return parseResponse<GenerateRollbackResponseVM>(response);
}

export async function generateAssetYamlMerge(actionId: number): Promise<GenerateAssetYamlMergeResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/actions/${actionId}/generate-asset-yaml-merge`, { method: "POST" });
  return parseResponse<GenerateAssetYamlMergeResponseVM>(response);
}


export async function listOrganizeTemplates(): Promise<OrganizeTemplateListResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/library/organize/templates`);
  return parseResponse<OrganizeTemplateListResponseVM>(response);
}
