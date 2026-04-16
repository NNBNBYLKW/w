import type { RecentListQueryInput, RecentListResponseVM } from "../../entities/recent/types";


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


export async function listRecentImports(input: RecentListQueryInput): Promise<RecentListResponseVM> {
  const params = new URLSearchParams();
  params.set("range", input.range);
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  params.set("sort_order", input.sort_order);

  const response = await fetch(`${getApiBaseUrl()}/recent?${params.toString()}`);
  return parseResponse<RecentListResponseVM>(response);
}
