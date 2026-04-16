import type { CreateSourceInput, SourceVM, UpdateSourceInput } from "../../entities/source/types";
import type { TriggerScanResult } from "../../entities/task/types";


type SourceListResponse = {
  items: SourceVM[];
};


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


export async function getSources(): Promise<SourceVM[]> {
  const response = await fetch(`${getApiBaseUrl()}/sources`);
  const payload = await parseResponse<SourceListResponse>(response);
  return payload.items;
}


export async function createSource(input: CreateSourceInput): Promise<SourceVM> {
  const response = await fetch(`${getApiBaseUrl()}/sources`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  return parseResponse<SourceVM>(response);
}


export async function updateSource(sourceId: number, input: UpdateSourceInput): Promise<SourceVM> {
  const response = await fetch(`${getApiBaseUrl()}/sources/${sourceId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  return parseResponse<SourceVM>(response);
}


export async function deleteSource(sourceId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/sources/${sourceId}`, {
    method: "DELETE",
  });
  await parseResponse<{ message: string }>(response);
}


export async function triggerSourceScan(sourceId: number): Promise<TriggerScanResult> {
  const response = await fetch(`${getApiBaseUrl()}/sources/${sourceId}/scan`, {
    method: "POST",
  });
  return parseResponse<TriggerScanResult>(response);
}
