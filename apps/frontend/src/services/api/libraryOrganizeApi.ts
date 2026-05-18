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
