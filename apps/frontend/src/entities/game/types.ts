import type { ColorTagValue, FileKind, FileListSortBy, FileListSortOrder, FileRatingValue, FileStatusValue, ManualPlacementValue, PlacementValue } from "../file/types";


export type GameFormat = string;

export type GamesListQueryInput = {
  status?: FileStatusValue;
  tag_id?: number;
  color_tag?: ColorTagValue;
  page: number;
  page_size: number;
  sort_by: FileListSortBy;
  sort_order: FileListSortOrder;
};

export type GameListItemVM = {
  id: number;
  display_title: string;
  game_format: GameFormat;
  file_kind: FileKind;
  auto_placement: PlacementValue;
  manual_placement: ManualPlacementValue | null;
  effective_placement: PlacementValue;
  path: string;
  modified_at: string;
  size_bytes: number | null;
  status: FileStatusValue | null;
  is_favorite: boolean;
  rating: FileRatingValue | null;
};

export type GamesListResponseVM = {
  items: GameListItemVM[];
  page: number;
  page_size: number;
  total: number;
};
