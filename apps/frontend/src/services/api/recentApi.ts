import { getApiBaseUrl, parseResponse } from "./client";
import type {
  RecentActivityListResponseVM,
  RecentListQueryInput,
  RecentListResponseVM,
} from "../../entities/recent/types";


export async function listRecentImports(input: RecentListQueryInput): Promise<RecentListResponseVM> {
  const params = new URLSearchParams();
  params.set("range", input.range);
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  params.set("sort_order", input.sort_order);

  const response = await fetch(`${getApiBaseUrl()}/recent?${params.toString()}`);
  return parseResponse<RecentListResponseVM>(response);
}


export async function listRecentTagged(input: RecentListQueryInput): Promise<RecentActivityListResponseVM> {
  const params = new URLSearchParams();
  params.set("range", input.range);
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  params.set("sort_order", input.sort_order);

  const response = await fetch(`${getApiBaseUrl()}/recent/tagged?${params.toString()}`);
  return parseResponse<RecentActivityListResponseVM>(response);
}


export async function listRecentColorTagged(input: RecentListQueryInput): Promise<RecentActivityListResponseVM> {
  const params = new URLSearchParams();
  params.set("range", input.range);
  params.set("page", String(input.page));
  params.set("page_size", String(input.page_size));
  params.set("sort_order", input.sort_order);

  const response = await fetch(`${getApiBaseUrl()}/recent/color-tagged?${params.toString()}`);
  return parseResponse<RecentActivityListResponseVM>(response);
}
