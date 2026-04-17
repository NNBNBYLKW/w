import type { TagItemVM } from "../tag/types";


export type FileType = "image" | "video" | "document" | "archive" | "other";
export type ColorTagValue = "red" | "yellow" | "green" | "blue" | "purple";

export type SearchSortBy = "modified_at" | "name" | "discovered_at";
export type SearchSortOrder = "asc" | "desc";
export type FileListSortBy = "modified_at" | "name" | "discovered_at";
export type FileListSortOrder = "asc" | "desc";

export type FilesListQueryInput = {
  source_id?: number;
  parent_path?: string;
  tag_id?: number;
  color_tag?: ColorTagValue;
  page: number;
  page_size: number;
  sort_by: FileListSortBy;
  sort_order: FileListSortOrder;
};

export type FilesListItemVM = {
  id: number;
  name: string;
  path: string;
  file_type: FileType;
  modified_at: string;
  size_bytes: number | null;
};

export type FilesListResponseVM = {
  items: FilesListItemVM[];
  page: number;
  page_size: number;
  total: number;
};

export type SearchQueryInput = {
  query?: string;
  file_type?: FileType;
  tag_id?: number;
  color_tag?: ColorTagValue;
  page: number;
  page_size: number;
  sort_by: SearchSortBy;
  sort_order: SearchSortOrder;
};

export type SearchResultItemVM = {
  id: number;
  name: string;
  path: string;
  file_type: FileType;
  modified_at: string;
};

export type SearchResponseVM = {
  items: SearchResultItemVM[];
  page: number;
  page_size: number;
  total: number;
};

export type FileDetailItemVM = {
  id: number;
  name: string;
  path: string;
  file_type: FileType;
  size_bytes: number | null;
  created_at_fs: string | null;
  modified_at_fs: string | null;
  discovered_at: string;
  last_seen_at: string;
  is_deleted: boolean;
  source_id: number;
  tags: TagItemVM[];
  color_tag: ColorTagValue | null;
  metadata:
    | {
        width: number | null;
        height: number | null;
        duration_ms: number | null;
        page_count: number | null;
      }
    | null;
};

export type FileDetailResponseVM = {
  item: FileDetailItemVM;
};

export type FileColorTagResponseVM = {
  item: {
    id: number;
    color_tag: ColorTagValue | null;
  };
};
