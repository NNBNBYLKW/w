import type { SearchQueryInput, SearchResponseVM } from "../../entities/file/types";


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
      | null;
    throw new Error(payload?.error?.message ?? "Request failed.");
  }
  return response.json() as Promise<T>;
}


export async function searchFiles(input: SearchQueryInput): Promise<SearchResponseVM> {
  const params = new URLSearchParams();
  const trimmedQuery = input.query?.trim() ?? "";

  if (trimmedQuery) {
    params.set("query", trimmedQuery);
  }
  if (input.file_type) {
    params.set("file_type", input.file_type);
  }

  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  params.set("sort_by", input.sort_by);
  params.set("sort_order", input.sort_order);

  const response = await fetch(`${getApiBaseUrl()}/search?${params.toString()}`);
  return parseResponse<SearchResponseVM>(response);
}
