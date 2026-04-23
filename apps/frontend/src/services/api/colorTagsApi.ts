import type { BatchColorTagUpdateResponseVM, FileColorTagResponseVM } from "../../entities/file/types";


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


export async function updateFileColorTag(
  fileId: number,
  colorTag: string | null,
): Promise<FileColorTagResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}/color-tag`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ color_tag: colorTag }),
  });
  return parseResponse<FileColorTagResponseVM>(response);
}


export async function updateFilesColorTagBatch(
  fileIds: number[],
  colorTag: string | null,
): Promise<BatchColorTagUpdateResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/batch/color-tag`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_ids: fileIds, color_tag: colorTag }),
  });
  return parseResponse<BatchColorTagUpdateResponseVM>(response);
}
