import type { FileListSortBy, FileListSortOrder } from "../file/types";


export type SoftwareFormat = "exe" | "msi" | "zip";

export type SoftwareListQueryInput = {
  page: number;
  page_size: number;
  sort_by: FileListSortBy;
  sort_order: FileListSortOrder;
};

export type SoftwareListItemVM = {
  id: number;
  display_title: string;
  software_format: SoftwareFormat;
  path: string;
  modified_at: string;
  size_bytes: number | null;
};

export type SoftwareListResponseVM = {
  items: SoftwareListItemVM[];
  page: number;
  page_size: number;
  total: number;
};
