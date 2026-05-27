import { getApiBaseUrl, parseResponse } from "./client";
import type { GamesListQueryInput, GamesListResponseVM } from "../../entities/game/types";


export async function listGames(input: GamesListQueryInput): Promise<GamesListResponseVM> {
  const params = new URLSearchParams();
  if (input.status) {
    params.set("status", input.status);
  }
  if (input.tag_id) {
    params.set("tag_id", String(input.tag_id));
  }
  if (input.color_tag) {
    params.set("color_tag", input.color_tag);
  }
  if (input.storage_state) {
    params.set("storage_state", input.storage_state);
  }
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  params.set("sort_by", input.sort_by);
  params.set("sort_order", input.sort_order);

  const response = await fetch(`${getApiBaseUrl()}/library/games?${params.toString()}`);
  return parseResponse<GamesListResponseVM>(response);
}
