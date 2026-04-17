import type { FileListSortBy, FileListSortOrder, FileType } from "../file/types";


export type TagItemVM = {
  id: number;
  name: string;
};

export type TagResponseVM = {
  item: TagItemVM;
};

export type TagListResponseVM = {
  items: TagItemVM[];
};

export type TagFilesQueryInput = {
  tagId: number;
  page: number;
  page_size: number;
  sort_by: FileListSortBy;
  sort_order: FileListSortOrder;
};

export type TagFilesListItemVM = {
  id: number;
  name: string;
  path: string;
  file_type: FileType;
  modified_at: string;
  size_bytes: number | null;
};

export type TagFilesListResponseVM = {
  items: TagFilesListItemVM[];
  page: number;
  page_size: number;
  total: number;
};
