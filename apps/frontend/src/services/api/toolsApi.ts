import type {
  ToolListResponseVM,
  ToolRunCreateResponseVM,
  ToolRunListResponseVM,
  ToolRunVM,
  VideoMergeRunCreateInput,
} from "../../entities/tool/types";


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
    throw new Error("Request failed.");
  }
  return response.json() as Promise<T>;
}


export async function listTools(): Promise<ToolListResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/tools`);
  return parseResponse<ToolListResponseVM>(response);
}


export async function createVideoMergeRun(input: VideoMergeRunCreateInput): Promise<ToolRunCreateResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/tools/video-merge/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<ToolRunCreateResponseVM>(response);
}


export async function getToolRun(runId: number): Promise<ToolRunVM> {
  const response = await fetch(`${getApiBaseUrl()}/tools/runs/${runId}`);
  return parseResponse<ToolRunVM>(response);
}


export async function listToolRuns(input: { page: number; page_size: number }): Promise<ToolRunListResponseVM> {
  const params = new URLSearchParams();
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  const response = await fetch(`${getApiBaseUrl()}/tools/runs?${params.toString()}`);
  return parseResponse<ToolRunListResponseVM>(response);
}
