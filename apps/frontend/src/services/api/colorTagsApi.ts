import { getApiBaseUrl, parseResponse } from "./client";
import type { BatchColorTagUpdateResponseVM, FileColorTagResponseVM } from "../../entities/file/types";


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
