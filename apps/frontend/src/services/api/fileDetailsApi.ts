import { getApiBaseUrl, parseResponse } from "./client";
import type { FileDetailResponseVM } from "../../entities/file/types";


export type FileVideoPreviewResponseVM = {
  item: {
    id: number;
    frame_count: number;
    frame_indexes: number[];
  };
};

export type ThumbnailWarmupResponseVM = {
  cached: number[];
  queued: number[];
  in_progress: number[];
  unsupported: number[];
  missing: number[];
  failed: number[];
};


export function getFileThumbnailUrl(fileId: number): string {
  return `${getApiBaseUrl()}/files/${fileId}/thumbnail`;
}

export function getFilePosterUrl(fileId: number): string {
  return `${getApiBaseUrl()}/files/${fileId}/poster`;
}

export function getFileVideoPreviewFrameUrl(fileId: number, frameIndex: number): string {
  return `${getApiBaseUrl()}/files/${fileId}/video-preview/frames/${frameIndex}`;
}


export async function getFileDetails(fileId: number): Promise<FileDetailResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}`);
  return parseResponse<FileDetailResponseVM>(response);
}

export async function warmupFileThumbnails(fileIds: number[]): Promise<ThumbnailWarmupResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/thumbnails/warmup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ file_ids: fileIds }),
  });
  return parseResponse<ThumbnailWarmupResponseVM>(response);
}

export async function getFileVideoPreview(fileId: number): Promise<FileVideoPreviewResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}/video-preview`);
  return parseResponse<FileVideoPreviewResponseVM>(response);
}

export type SiblingFileVM = {
  id: number;
  name: string;
  path: string;
  file_type: string;
  modified_at: string;
};

export type SiblingFilesResponseVM = {
  items: SiblingFileVM[];
};

export async function getSiblingFiles(fileId: number, limit: number = 20): Promise<SiblingFilesResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}/siblings?limit=${limit}`);
  return parseResponse<SiblingFilesResponseVM>(response);
}
