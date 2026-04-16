import type { FileListSortOrder, FileType } from "../file/types";


export type RecentRangeValue = "1d" | "7d" | "30d";

export type RecentListQueryInput = {
  range: RecentRangeValue;
  page: number;
  page_size: number;
  sort_order: FileListSortOrder;
};

export type RecentListItemVM = {
  id: number;
  name: string;
  path: string;
  file_type: FileType;
  discovered_at: string;
  size_bytes: number | null;
};

export type RecentListResponseVM = {
  items: RecentListItemVM[];
  page: number;
  page_size: number;
  total: number;
};
