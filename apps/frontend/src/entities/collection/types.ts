import type { ColorTagValue, FileListSortBy, FileListSortOrder, FileType, FilesListItemVM, FilesListResponseVM } from "../file/types";


export type CollectionVM = {
  id: number;
  name: string;
  file_type: FileType | null;
  tag_id: number | null;
  color_tag: ColorTagValue | null;
  source_id: number | null;
  parent_path: string | null;
  created_at: string;
  updated_at: string;
};

export type CollectionListResponseVM = {
  items: CollectionVM[];
};

export type CreateCollectionInput = {
  name: string;
  file_type?: FileType;
  tag_id?: number;
  color_tag?: ColorTagValue;
  source_id?: number;
  parent_path?: string;
};

export type CollectionFilesQueryInput = {
  collectionId: number;
  page: number;
  page_size: number;
  sort_by: FileListSortBy;
  sort_order: FileListSortOrder;
};

export type CollectionFilesListItemVM = FilesListItemVM;
export type CollectionFilesListResponseVM = FilesListResponseVM;
