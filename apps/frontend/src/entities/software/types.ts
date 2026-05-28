import type { ColorTagValue, FileKind, FileListSortBy, FileListSortOrder, FileRatingValue, ManualPlacementValue, PlacementValue, StorageStateFilter } from "../file/types";


export type SoftwareFormat = string;

export type SoftwareListQueryInput = {
  tag_id?: number;
  color_tag?: ColorTagValue;
  storage_state?: StorageStateFilter;
  page: number;
  page_size: number;
  sort_by: FileListSortBy;
  sort_order: FileListSortOrder;
};

export type SoftwareListItemVM = {
  id: number;
  display_title: string;
  software_format: SoftwareFormat;
  file_kind: FileKind;
  auto_placement: PlacementValue;
  manual_placement: ManualPlacementValue | null;
  effective_placement: PlacementValue;
  path: string;
  modified_at: string;
  size_bytes: number | null;
  is_favorite: boolean;
  rating: FileRatingValue | null;
};

export type SoftwareListResponseVM = {
  items: SoftwareListItemVM[];
  page: number;
  page_size: number;
  total: number;
};
