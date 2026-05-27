import { getApiBaseUrl, parseResponse } from "./client";
import type { BookListQueryInput, BooksListResponseVM } from "../../entities/book/types";


export async function listBooks(input: BookListQueryInput): Promise<BooksListResponseVM> {
  const params = new URLSearchParams();
  if (input.tag_id !== undefined) {
    params.set("tag_id", String(input.tag_id));
  }
  if (input.color_tag !== undefined) {
    params.set("color_tag", input.color_tag);
  }
  if (input.storage_state) {
    params.set("storage_state", input.storage_state);
  }
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  params.set("sort_by", input.sort_by);
  params.set("sort_order", input.sort_order);

  const response = await fetch(`${getApiBaseUrl()}/library/books?${params.toString()}`);
  return parseResponse<BooksListResponseVM>(response);
}
