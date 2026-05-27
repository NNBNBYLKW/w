import { getApiBaseUrl, parseResponse } from "./client";
import type {
  BatchPlacementUpdateResponseVM,
  FilePlacementResponseVM,
  FileRatingValue,
  FileUserMetaResponseVM,
  ManualPlacementValue,
} from "../../entities/file/types";


export async function updateFileUserMeta(
  fileId: number,
  payload: {
    is_favorite?: boolean;
    rating?: FileRatingValue | null;
  },
): Promise<FileUserMetaResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}/user-meta`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<FileUserMetaResponseVM>(response);
}

export async function updateFilePlacement(
  fileId: number,
  manualPlacement: ManualPlacementValue | null,
): Promise<FilePlacementResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}/placement`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ manual_placement: manualPlacement }),
  });
  return parseResponse<FilePlacementResponseVM>(response);
}

export async function updateFilesPlacementBatch(
  fileIds: number[],
  manualPlacement: ManualPlacementValue | null,
): Promise<BatchPlacementUpdateResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/batch/placement`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_ids: fileIds, manual_placement: manualPlacement }),
  });
  return parseResponse<BatchPlacementUpdateResponseVM>(response);
}
