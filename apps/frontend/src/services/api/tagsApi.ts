import type { TagFilesListResponseVM, TagFilesQueryInput, TagListResponseVM, TagResponseVM } from "../../entities/tag/types";


export class TagsApiError extends Error {
  code: string | null;

  constructor(message: string, code: string | null = null) {
    super(message);
    this.name = "TagsApiError";
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
    throw new TagsApiError(payload?.error?.message ?? "Request failed.", payload?.error?.code ?? null);
  }
  return response.json() as Promise<T>;
}


export async function listTags(): Promise<TagListResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/tags`);
  return parseResponse<TagListResponseVM>(response);
}


export async function createTag(name: string): Promise<TagResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/tags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return parseResponse<TagResponseVM>(response);
}


export async function attachTagToFile(fileId: number, name: string): Promise<TagListResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}/tags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return parseResponse<TagListResponseVM>(response);
}


export async function removeTagFromFile(fileId: number, tagId: number): Promise<TagListResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}/tags/${tagId}`, {
    method: "DELETE",
  });
  return parseResponse<TagListResponseVM>(response);
}


export async function listFilesForTag(tagId: number, params: Omit<TagFilesQueryInput, "tagId">): Promise<TagFilesListResponseVM> {
  const searchParams = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.page_size),
    sort_by: params.sort_by,
    sort_order: params.sort_order,
  });
  const response = await fetch(`${getApiBaseUrl()}/tags/${tagId}/files?${searchParams.toString()}`);
  return parseResponse<TagFilesListResponseVM>(response);
}
