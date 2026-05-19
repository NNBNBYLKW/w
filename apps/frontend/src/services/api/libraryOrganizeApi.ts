function getApiBaseUrl() {
  const desktopApi = (
    window as typeof window & {
      assetWorkbench?: { getBackendBaseUrl?: () => string };
    }
  ).assetWorkbench;
  return desktopApi?.getBackendBaseUrl?.() ?? import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
}

const BASE = () => `${getApiBaseUrl()}/library/organize`;

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
