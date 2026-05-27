import { getApiBaseUrl, parseResponse } from "./client";
import type { FileStatusResponseVM, FileStatusValue } from "../../entities/file/types";


export async function updateFileStatus(
  fileId: number,
  status: FileStatusValue | null,
): Promise<FileStatusResponseVM> {
  const response = await fetch(`${getApiBaseUrl()}/files/${fileId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  return parseResponse<FileStatusResponseVM>(response);
}
