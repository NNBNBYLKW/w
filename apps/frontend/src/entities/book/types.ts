import type { ColorTagValue, FileListSortBy, FileListSortOrder, FileRatingValue } from "../file/types";


export type BookFormat = "epub" | "pdf";

export type BookListQueryInput = {
  tag_id?: number;
  color_tag?: ColorTagValue;
  page: number;
  page_size: number;
  sort_by: FileListSortBy;
  sort_order: FileListSortOrder;
};

export type BookListItemVM = {
  id: number;
  display_title: string;
  book_format: BookFormat;
  path: string;
  modified_at: string;
  size_bytes: number | null;
  is_favorite: boolean;
  rating: FileRatingValue | null;
};

export type BooksListResponseVM = {
  items: BookListItemVM[];
  page: number;
  page_size: number;
  total: number;
};
