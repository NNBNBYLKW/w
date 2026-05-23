function getApiBaseUrl() {
  const desktopApi = (
    window as typeof window & {
      assetWorkbench?: {
        getBackendBaseUrl?: () => string;
      };
    }
  ).assetWorkbench;
  return desktopApi?.getBackendBaseUrl?.() ?? import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
}

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

const BASE = () => `${getApiBaseUrl()}/library/import`;

export interface ImportBatchVM {
  id: number;
  status: string;
  source_kind: string;
  import_method: string;
  file_count: number;
  completed_count: number;
  failed_count: number;
  created_at: string;
  finished_at: string | null;
  error_summary: string | null;
}

export interface ImportBatchListResponse {
  items: ImportBatchVM[];
  total: number;
  page: number;
  page_size: number;
}

export interface InboxItemVM {
  id: number;
  import_batch_id: number;
  file_id: number | null;
  source_path: string;
  inbox_path: string;
  status: string;
  detected_file_kind: string | null;
  detected_placement: string | null;
  detected_object_type: string | null;
  final_object_type: string | null;
  target_library_root_id: number | null;
  organize_candidate_id: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface InboxItemListResponse {
  items: InboxItemVM[];
  total: number;
  page: number;
  page_size: number;
}

export interface ImportFilesResponse {
  batch_id: number;
  created_items: Array<{
    source_path: string;
    inbox_path: string;
    file_id: number;
    inbox_item_id: number;
  }>;
  failed_items: Array<{
    path: string;
    error: string;
  }>;
}

export async function createImportBatch(): Promise<ImportBatchVM> {
  const res = await fetch(`${BASE()}/batches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ import_method: "copy" }),
  });
  return parseResponse<ImportBatchVM>(res);
}

export async function listImportBatches(
  page = 1,
  pageSize = 50,
): Promise<ImportBatchListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  const res = await fetch(`${BASE()}/batches?${params}`);
  return parseResponse<ImportBatchListResponse>(res);
}

export async function getImportBatch(batchId: number): Promise<ImportBatchVM> {
  const res = await fetch(`${BASE()}/batches/${batchId}`);
  return parseResponse<ImportBatchVM>(res);
}

export async function importFilesToBatch(
  batchId: number,
  paths: string[],
): Promise<ImportFilesResponse> {
  const res = await fetch(`${BASE()}/batches/${batchId}/files`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paths }),
  });
  return parseResponse<ImportFilesResponse>(res);
}

export async function listInboxItems(
  page = 1,
  pageSize = 50,
  status?: string,
  batchId?: number,
): Promise<InboxItemListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) params.set("status", status);
  if (batchId != null) params.set("batch_id", String(batchId));
  const res = await fetch(`${BASE()}/inbox/items?${params}`);
  return parseResponse<InboxItemListResponse>(res);
}

export async function getInboxItem(itemId: number): Promise<InboxItemVM> {
  const res = await fetch(`${BASE()}/inbox/items/${itemId}`);
  return parseResponse<InboxItemVM>(res);
}

// ── Folder Import ──────────────────────────────────────

export interface ImportFolderResponse {
  batch_id: number;
  object_candidates: Array<{
    object_candidate_id: number;
    suggested_object_type: string;
    confidence: string;
    member_count: number;
    members: Array<{
      relative_path: string;
      file_id: number;
      inbox_item_id: number;
      role: string;
    }>;
  }>;
  created_items: Array<Record<string, unknown>>;
  failed_items: Array<{ path: string; error: string }>;
}

export async function importFolderToBatch(
  batchId: number,
  paths: string[],
  mode: "object" | "loose_files" = "object",
): Promise<ImportFolderResponse> {
  const res = await fetch(`${BASE()}/batches/${batchId}/folders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paths, mode }),
  });
  return parseResponse<ImportFolderResponse>(res);
}

// ── Object Candidates ──────────────────────────────────

export interface ObjectCandidateVM {
  id: number;
  import_batch_id: number;
  source_root_path: string;
  inbox_root_path: string;
  suggested_object_type: string | null;
  final_object_type: string | null;
  confidence: string | null;
  status: string;
  primary_file_id: number | null;
  launch_file_id: number | null;
  member_count: number;
  reason_json: string | null;
  created_at: string | null;
}

export interface ObjectCandidateMemberVM {
  id: number;
  inbox_item_id: number;
  role: string;
  confidence: string | null;
  reason: string | null;
  source_path: string | null;
  inbox_path: string | null;
  file_id: number | null;
}

export interface ObjectCandidateDetailVM extends ObjectCandidateVM {
  members: ObjectCandidateMemberVM[];
}

export interface ObjectCandidateListResponse {
  items: ObjectCandidateVM[];
  total: number;
  page: number;
  page_size: number;
}

export async function listObjectCandidates(
  page = 1,
  pageSize = 50,
): Promise<ObjectCandidateListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  const res = await fetch(`${BASE()}/object-candidates?${params}`);
  return parseResponse<ObjectCandidateListResponse>(res);
}

export async function getObjectCandidate(
  candidateId: number,
): Promise<ObjectCandidateDetailVM> {
  const res = await fetch(`${BASE()}/object-candidates/${candidateId}`);
  return parseResponse<ObjectCandidateDetailVM>(res);
}

export async function updateObjectCandidate(
  candidateId: number,
  data: { final_object_type?: string; launch_file_id?: number },
): Promise<ObjectCandidateVM> {
  const res = await fetch(`${BASE()}/object-candidates/${candidateId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return parseResponse<ObjectCandidateVM>(res);
}

// ── Inbox Item Review ──────────────────────────────────

export async function updateInboxItem(
  itemId: number,
  data: { final_object_type?: string; target_library_root_id?: number },
): Promise<InboxItemVM> {
  const res = await fetch(`${BASE()}/inbox/items/${itemId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return parseResponse<InboxItemVM>(res);
}

export async function confirmInboxItem(
  itemId: number,
  data: { final_object_type: string; target_library_root_id?: number },
): Promise<InboxItemVM> {
  const res = await fetch(`${BASE()}/inbox/items/${itemId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return parseResponse<InboxItemVM>(res);
}

export async function rejectInboxItem(itemId: number): Promise<InboxItemVM> {
  const res = await fetch(`${BASE()}/inbox/items/${itemId}/reject`, { method: "POST" });
  return parseResponse<InboxItemVM>(res);
}

export async function createCandidateFromInboxItem(itemId: number): Promise<{ candidate_id: number }> {
  const res = await fetch(`${BASE()}/inbox/items/${itemId}/create-candidate`, { method: "POST" });
  return parseResponse<{ candidate_id: number }>(res);
}

// ── Object Candidate Review ────────────────────────────

export async function confirmObjectCandidate(
  candidateId: number,
  data: { final_object_type: string; launch_file_id?: number; target_library_root_id?: number },
): Promise<ObjectCandidateVM> {
  const res = await fetch(`${BASE()}/object-candidates/${candidateId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return parseResponse<ObjectCandidateVM>(res);
}

export async function rejectObjectCandidate(candidateId: number): Promise<ObjectCandidateVM> {
  const res = await fetch(`${BASE()}/object-candidates/${candidateId}/reject`, { method: "POST" });
  return parseResponse<ObjectCandidateVM>(res);
}

export async function createCandidateFromObjectCandidate(
  candidateId: number,
): Promise<{ candidate_id: number; import_object_candidate_id: number }> {
  const res = await fetch(`${BASE()}/object-candidates/${candidateId}/create-candidate`, { method: "POST" });
  return parseResponse<{ candidate_id: number; import_object_candidate_id: number }>(res);
}

// ── Generate Draft Plan ────────────────────────────────

export async function generateDraftPlan(candidateIds: number[]): Promise<{
  plan_id: number; status: string; actions_count: number; blocked_count: number; warning_count: number;
}> {
  const res = await fetch(`${BASE()}/organize-plans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_ids: candidateIds }),
  });
  return parseResponse(res);
}

// ── Phase 7H-3: Multi-file Collection Import ────────────

export interface ImportFileCollectionRequest {
  paths: string[];
  collection_name: string;
  suggested_object_type?: string;
  target_library_root_id?: number;
}

export interface ImportFileCollectionMember {
  relative_path: string;
  file_id: number;
  inbox_item_id: number;
  role: string;
}

export interface ImportFileCollectionResponse {
  batch_id: number;
  object_candidate_id: number;
  suggested_object_type: string | null;
  confidence: string | null;
  member_count: number;
  members: ImportFileCollectionMember[];
  failed_items: Array<{ path: string; error: string }>;
}

export async function importFileCollection(
  data: ImportFileCollectionRequest,
): Promise<ImportFileCollectionResponse> {
  const res = await fetch(`${BASE()}/file-collections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return parseResponse<ImportFileCollectionResponse>(res);
}

// ── Phase 8C-1: Compose inbox items ─────────────────────

export interface ComposeInboxRequest {
  inbox_item_ids: number[];
  object_name: string;
  suggested_object_type?: string;
  target_library_root_id?: number;
}

export interface ComposeInboxResponse {
  object_candidate_id: number;
  import_batch_id: number;
  object_name: string;
  suggested_object_type: string | null;
  confidence: string;
  member_count: number;
  members: Array<{ inbox_item_id: number; file_id: number; role: string }>;
  notes: string[];
}

export async function composeInboxItems(
  data: ComposeInboxRequest,
): Promise<ComposeInboxResponse> {
  const res = await fetch(`${BASE()}/compose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const payload = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail || "Compose failed.");
  }
  return res.json() as Promise<ComposeInboxResponse>;
}

// ── Phase 8C-3: Compose external files ───────────────────

export interface ComposeExternalRequest {
  file_ids: number[];
  object_name: string;
  suggested_object_type?: string;
  target_library_root_id?: number;
}

export interface ComposeExternalResponse {
  import_batch_id: number;
  object_candidate_id: number;
  object_name: string;
  suggested_object_type: string | null;
  confidence: string;
  member_count: number;
  copied_count: number;
  status: string;
  members: Array<{ file_id: number; inbox_item_id: number; source_file_id: string; name: string; role: string }>;
  notes: string[];
}

export async function composeExternalFiles(
  data: ComposeExternalRequest,
): Promise<ComposeExternalResponse> {
  const res = await fetch(`${BASE()}/compose/external-files`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const payload = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail || "Compose failed.");
  }
  return res.json() as Promise<ComposeExternalResponse>;
}

export interface RecentOperation {
  id: number;
  operation_id: string;
  operation_type: string;
  entity_type: string;
  entity_id: number;
  status: string;
  before_json: string | null;
  after_json: string | null;
  created_at: string;
}

export async function getRecentOperations(limit = 10): Promise<{ items: RecentOperation[]; total: number }> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/library/import/recent-operations?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch recent operations");
  return res.json();
}
