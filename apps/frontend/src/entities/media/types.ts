import type { FileListSortBy, FileListSortOrder } from "../file/types";


export type MediaViewScope = "all" | "image" | "video";

export type MediaListQueryInput = {
  view_scope: MediaViewScope;
  page: number;
  page_size: number;
  sort_by: FileListSortBy;
  sort_order: FileListSortOrder;
};

export type MediaListItemVM = {
  id: number;
  name: string;
  path: string;
  file_type: "image" | "video";
  modified_at: string;
  size_bytes: number | null;
};

export type MediaListResponseVM = {
  items: MediaListItemVM[];
  page: number;
  page_size: number;
  total: number;
};
