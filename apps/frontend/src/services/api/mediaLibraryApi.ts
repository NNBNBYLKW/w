import { getApiBaseUrl, parseResponse } from "./client";
import type { MediaListQueryInput, MediaListResponseVM } from "../../entities/media/types";


export async function listMediaLibrary(input: MediaListQueryInput): Promise<MediaListResponseVM> {
  const params = new URLSearchParams();
  params.set("view_scope", input.view_scope);
  if (input.storage_state) {
    params.set("storage_state", input.storage_state);
  }
  if (input.tag_id !== undefined) {
    params.set("tag_id", String(input.tag_id));
  }
  if (input.color_tag !== undefined) {
    params.set("color_tag", input.color_tag);
  }
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  params.set("sort_by", input.sort_by);
  params.set("sort_order", input.sort_order);

  const response = await fetch(`${getApiBaseUrl()}/library/media?${params.toString()}`);
  return parseResponse<MediaListResponseVM>(response);
}
