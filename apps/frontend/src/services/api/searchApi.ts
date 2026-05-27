import { getApiBaseUrl, parseResponse } from "./client";
import type { SearchQueryInput, SearchResponseVM } from "../../entities/file/types";


export async function searchFiles(input: SearchQueryInput): Promise<SearchResponseVM> {
  const params = new URLSearchParams();
  const trimmedQuery = input.query?.trim() ?? "";

  if (trimmedQuery) {
    params.set("query", trimmedQuery);
  }
  if (input.file_type) {
    params.set("file_type", input.file_type);
  }
  if (input.library_placement) {
    params.set("library_placement", input.library_placement);
  }
  if (input.storage_state) {
    params.set("storage_state", input.storage_state);
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

  const response = await fetch(`${getApiBaseUrl()}/search?${params.toString()}`);
  return parseResponse<SearchResponseVM>(response);
}
