import type { GamesListQueryInput, GamesListResponseVM } from "../../entities/game/types";


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


export async function listGames(input: GamesListQueryInput): Promise<GamesListResponseVM> {
  const params = new URLSearchParams();
  if (input.status) {
    params.set("status", input.status);
  }
  if (input.tag_id) {
    params.set("tag_id", String(input.tag_id));
  }
  if (input.color_tag) {
    params.set("color_tag", input.color_tag);
  }
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  params.set("sort_by", input.sort_by);
  params.set("sort_order", input.sort_order);

  const response = await fetch(`${getApiBaseUrl()}/library/games?${params.toString()}`);
  return parseResponse<GamesListResponseVM>(response);
}
