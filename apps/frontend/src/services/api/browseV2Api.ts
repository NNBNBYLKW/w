function getApiBaseUrl() {
  const desktopApi = (
    window as typeof window & {
      assetWorkbench?: { getBackendBaseUrl?: () => string };
    }
  ).assetWorkbench;
  return desktopApi?.getBackendBaseUrl?.() ?? import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    if (payload && "detail" in payload) {
      throw new Error(typeof payload.detail === "string" ? payload.detail : "Request failed.");
    }
    throw new Error("Request failed.");
  }
  return response.json() as Promise<T>;
}

const BASE = () => `${getApiBaseUrl()}/library/browse`;

export interface BrowseV2ObjectCard {
  card_kind: "object";
  namespaced_id: string;
  object_source: string;
  source_id: number;
  object_type: string | null;
  display_title: string;
  member_count: number;
  storage_state: string | null;
  root_path: string | null;
  needs_review: boolean;
  confidence: string | null;
  badges: string[];
}

export interface BrowseV2LooseFileCard {
  card_kind: "loose_file";
  file_id: number;
  name: string;
  file_kind: string | null;
  path: string;
  storage_state: string | null;
  size_bytes: number | null;
  modified_at: string | null;
  badges: string[];
}

export type BrowseV2Card = BrowseV2ObjectCard | BrowseV2LooseFileCard;

export interface BrowseV2Summary {
  total_objects: number;
  total_loose_files: number;
  managed_objects: number;
  inbox_objects: number;
  external_loose: number;
}

export interface BrowseV2Response {
  items: BrowseV2Card[];
  summary: BrowseV2Summary;
  total: number;
  page: number;
  page_size: number;
}

export async function listBrowseCards(params: {
  domain?: string;
  category?: string;
  storage_state?: string;
  card_kind?: string;
  page?: number;
  page_size?: number;
}): Promise<BrowseV2Response> {
  const sp = new URLSearchParams();
  if (params.domain) sp.set("domain", params.domain);
  if (params.category) sp.set("category", params.category);
  if (params.storage_state) sp.set("storage_state", params.storage_state);
  if (params.card_kind) sp.set("card_kind", params.card_kind);
  if (params.page) sp.set("page", String(params.page));
  if (params.page_size) sp.set("page_size", String(params.page_size));
  const res = await fetch(`${BASE()}?${sp}`);
  return parseResponse<BrowseV2Response>(res);
}
