function getApiBaseUrl() {
  const desktopApi = (
    window as typeof window & {
      assetWorkbench?: { getBackendBaseUrl?: () => string };
    }
  ).assetWorkbench;
  return desktopApi?.getBackendBaseUrl?.() ?? import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
}

const BASE = () => `${getApiBaseUrl()}/library/organize`;

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { error?: { message?: string } }
      | { detail?: unknown }
      | null;
    if (payload && "error" in payload) {
      throw new Error(payload.error?.message ?? "Request failed.");
    }
    if (payload && "detail" in payload) {
      throw new Error(typeof payload.detail === "string" ? payload.detail : "Request failed.");
    }
    throw new Error("Request failed.");
  }
  return response.json() as Promise<T>;
}

export interface ManagedComposePlanMember {
  file_id: number;
  role: string;
  relative_path: string;
  source_path: string | null;
  target_path: string | null;
}

export interface ManagedComposePlanResponse {
  plan_id: number;
  status: string;
  plan_kind: string;
  actions_count: number;
  target_library_root_id: number | null;
  target_root_path: string | null;
  target_object_dir: string;
  planned_members: ManagedComposePlanMember[];
  notes: string[];
}

export interface ManagedComposePlanRequest {
  file_ids: number[];
  object_name: string;
  object_type: string;
  target_library_root_id?: number;
}

export async function createManagedComposePlan(
  data: ManagedComposePlanRequest,
): Promise<ManagedComposePlanResponse> {
  const res = await fetch(`${BASE()}/plans/managed-compose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const payload = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail || "Failed to create managed compose plan.");
  }
  return res.json() as Promise<ManagedComposePlanResponse>;
}

// ── Phase 8D-D: Object Amendment ────────────────────────

export interface AmendmentPlanRequestParams {
  object_id: number;
  add_file_ids: number[];
  remove_member_ids: number[];
  target_library_root_id?: number;
  remove_target_policy?: string;
}

export interface AmendmentPlannedAction {
  action_type: string;
  source_path: string | null;
  target_path: string | null;
  file_id: number | null;
  member_role: string | null;
  amendment_action: string | null;
}

export interface AmendmentPlanResponse {
  plan_id: number;
  plan_kind: string;
  object_id: number;
  amendment_type: string;
  status: string;
  add_count: number;
  remove_count: number;
  planned_actions: AmendmentPlannedAction[];
  notes: string[];
}

const OBJ_BASE = () => `${getApiBaseUrl()}/library/objects`;

export async function createObjectAmendmentPlan(
  objectId: number,
  data: { add_file_ids: number[]; remove_member_ids: number[]; target_library_root_id?: number; remove_target_policy?: string },
): Promise<AmendmentPlanResponse> {
  const res = await fetch(`${OBJ_BASE()}/${objectId}/amendment-plans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const payload = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail || "Failed to create amendment plan.");
  }
  return res.json() as Promise<AmendmentPlanResponse>;
}

// ── Phase 8E: Plan Prepare & Execute ──────────────────────

export interface PreparePlanResponse {
  plan_id: number;
  can_execute: boolean;
  blocked_count: number;
  warning_count: number;
  actions: Array<{
    id: number; action_order: number; action_type: string;
    source_path: string | null; target_path: string | null;
    status: string; conflict_status: string; conflict_message: string | null;
  }>;
  messages: string[];
}

export async function preparePlan(planId: number): Promise<PreparePlanResponse> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/library/organize/plans/${planId}/prepare`, { method: "POST" });
  return parseResponse(res);
}

export interface ExecutePlanResponse {
  plan_id: number; status: string; execution_summary_json?: string;
}

export async function executePlan(planId: number): Promise<ExecutePlanResponse> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/library/organize/plans/${planId}/execute?confirm=true`, { method: "POST" });
  return parseResponse(res);
}
