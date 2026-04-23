import type {
  CollectionFilesListResponseVM,
  CollectionFilesQueryInput,
  CollectionListResponseVM,
  CollectionVM,
  CreateCollectionInput,
  UpdateCollectionInput,
} from "../../entities/collection/types";


export class CollectionsApiError extends Error {
  code: string | null;

  constructor(message: string, code: string | null = null) {
    super(message);
    this.name = "CollectionsApiError";
    this.code = code;
  }
}


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
      | { error?: { code?: string; message?: string } }
      | null;
    throw new CollectionsApiError(payload?.error?.message ?? "Request failed.", payload?.error?.code ?? null);
  }
  return response.json() as Promise<T>;
}


export async function listCollections(): Promise<CollectionListResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/collections`);
  return parseResponse<CollectionListResponseVM>(response);
}


export async function createCollection(input: CreateCollectionInput): Promise<CollectionVM> {
  const response = await fetch(`${getApiBaseUrl()}/collections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<CollectionVM>(response);
}


export async function deleteCollection(collectionId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/collections/${collectionId}`, {
    method: "DELETE",
  });
  await parseResponse<{ message: string }>(response);
}


export async function updateCollection(collectionId: number, input: UpdateCollectionInput): Promise<CollectionVM> {
  const response = await fetch(`${getApiBaseUrl()}/collections/${collectionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<CollectionVM>(response);
}


export async function listCollectionFiles(input: CollectionFilesQueryInput): Promise<CollectionFilesListResponseVM> {
  const params = new URLSearchParams({
    page: String(input.page),
    page_size: String(input.page_size),
    sort_by: input.sort_by,
    sort_order: input.sort_order,
  });
  const response = await fetch(`${getApiBaseUrl()}/collections/${input.collectionId}/files?${params.toString()}`);
  return parseResponse<CollectionFilesListResponseVM>(response);
}
