import { getApiBaseUrl, parseResponse } from "./client";
import type { FilesListQueryInput, FilesListResponseVM } from "../../entities/file/types";


export async function listIndexedFiles(input: FilesListQueryInput): Promise<FilesListResponseVM> {
  const params = new URLSearchParams();
  if (input.source_id !== undefined) {
    params.set("source_id", String(input.source_id));
  }
  if (input.parent_path !== undefined) {
    params.set("parent_path", input.parent_path);
  }
  if (input.file_kind !== undefined) {
    params.set("file_kind", input.file_kind);
  }
  if (input.tag_id !== undefined) {
    params.set("tag_id", String(input.tag_id));
  }
  if (input.color_tag) {
    params.set("color_tag", input.color_tag);
  }
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  params.set("sort_by", input.sort_by);
  params.set("sort_order", input.sort_order);

  const response = await fetch(`${getApiBaseUrl()}/files?${params.toString()}`);
  return parseResponse<FilesListResponseVM>(response);
}
