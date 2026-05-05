import type { FileDetailResponseVM } from "../../entities/file/types";


export type FileVideoPreviewResponseVM = {
  item: {
    id: number;
    frame_count: number;
    frame_indexes: number[];
  };
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

export function getFileThumbnailUrl(fileId: number): string {
  return `${getApiBaseUrl()}/files/${fileId}/thumbnail`;
}

export function getFileVideoPreviewFrameUrl(fileId: number, frameIndex: number): string {
  return `${getApiBaseUrl()}/files/${fileId}/video-preview/frames/${frameIndex}`;
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


export async function getFileDetails(fileId: number): Promise<FileDetailResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}`);
  return parseResponse<FileDetailResponseVM>(response);
}

export async function getFileVideoPreview(fileId: number): Promise<FileVideoPreviewResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}/video-preview`);
  return parseResponse<FileVideoPreviewResponseVM>(response);
}
