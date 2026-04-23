import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { BatchActionBar } from "../batch-organize/BatchActionBar";
import { useBatchOrganizeActions } from "../batch-organize/useBatchOrganizeActions";
import { useBatchSelection } from "../batch-organize/useBatchSelection";
import type { ColorTagValue, FileListSortBy, FileListSortOrder } from "../../entities/file/types";
import type { BookFormat } from "../../entities/book/types";
import { listBooks } from "../../services/api/booksApi";
import { listTags } from "../../services/api/tagsApi";
import {
  hasDesktopOpenActionsBridge,
  normalizeIndexedFilePath,
  openIndexedFile,
} from "../../services/desktop/openActions";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}

function formatBookFormat(value: BookFormat): string {
  return value.toUpperCase();
}

function formatModifiedAt(value: string): string {
  return new Date(value).toLocaleString();
}

function buildBookEntryLabel(value: BookFormat): string {
  return value === "epub" ? "Ebook entry" : "Document edition";
}

function buildBookFormatCopy(value: BookFormat): string {
  return value === "epub" ? "EPUB ebook" : "PDF edition";
}

function buildBookFormatHint(value: BookFormat): string {
  return value === "epub" ? "Flow-friendly ebook file" : "Paged document-style ebook";
}

function formatColorTagLabel(value: ColorTagValue): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

const COLOR_TAG_OPTIONS: ColorTagValue[] = ["red", "yellow", "green", "blue", "purple"];

function BooksLibraryCard({
  bookFormat,
  displayTitle,
  isFavorite,
  isBatchMode,
  modifiedAt,
  path,
  rating,
  selected,
  sizeBytes,
  onSelect,
}: {
  bookFormat: BookFormat;
  displayTitle: string;
  isFavorite: boolean;
  isBatchMode: boolean;
  modifiedAt: string;
  path: string;
  rating: number | null;
  selected: boolean;
  sizeBytes: number | null;
  onSelect: () => void;
}) {
  const hasDesktopOpenActions = hasDesktopOpenActionsBridge();

  const handleDoubleClick = async () => {
    if (!hasDesktopOpenActions) {
      return;
    }

    const normalizedPath = normalizeIndexedFilePath(path);
    if (!normalizedPath) {
      return;
    }

    await openIndexedFile(normalizedPath);
  };

  return (
    <button
      className={`books-card${selected ? " books-card--selected" : ""}`}
      type="button"
      onClick={onSelect}
      onDoubleClick={() => {
        if (isBatchMode) {
          return;
        }
        void handleDoubleClick();
      }}
    >
      <div className={`books-card__poster books-card__poster--${bookFormat}`}>
        <span className="books-card__spine" aria-hidden="true" />
        <div className="books-card__poster-copy">
          <span className="books-card__poster-icon" aria-hidden="true">
            {bookFormat === "epub" ? "EP" : "PDF"}
          </span>
          <strong>{buildBookEntryLabel(bookFormat)}</strong>
          <span>{buildBookFormatHint(bookFormat)}</span>
        </div>
      </div>
      <div className="books-card__body">
        <strong title={displayTitle}>{displayTitle}</strong>
        <span className={`books-card__entry-note books-card__entry-note--${bookFormat}`}>{buildBookFormatCopy(bookFormat)}</span>
        <p title={path}>{path}</p>
      </div>
      <div className="books-card__meta">
        <span className="status-pill">{formatBookFormat(bookFormat)}</span>
        <span className="status-pill">{formatBytes(sizeBytes)}</span>
        <span className="status-pill">{formatModifiedAt(modifiedAt)}</span>
        {isFavorite ? <span className="status-pill status-pill--favorite">★ Favorite</span> : null}
        {rating !== null ? <span className="status-pill status-pill--rating">★ {rating}</span> : null}
        {isBatchMode && selected ? <span className="status-pill">Selected</span> : null}
      </div>
      <span className="books-card__hint">Single-click for shared details. Double-click to open the indexed file.</span>
    </button>
  );
}

function BooksCardSkeleton() {
  return (
    <div className="books-card books-card--skeleton" aria-hidden="true">
      <div className="books-card__poster books-card__poster--skeleton" />
      <div className="books-card__body books-card__body--skeleton">
        <span className="books-card__skeleton-line books-card__skeleton-line--title" />
        <span className="books-card__skeleton-line books-card__skeleton-line--path" />
        <span className="books-card__skeleton-line books-card__skeleton-line--path-short" />
      </div>
      <div className="books-card__meta books-card__meta--skeleton">
        <span className="books-card__skeleton-pill" />
        <span className="books-card__skeleton-pill" />
        <span className="books-card__skeleton-pill" />
      </div>
    </div>
  );
}


export function BooksFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sortBy, setSortBy] = useState<FileListSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");
  const [tagFilter, setTagFilter] = useState<number | null>(null);
  const [colorTagFilter, setColorTagFilter] = useState<ColorTagValue | null>(null);
  const [page, setPage] = useState(1);
  const entry = searchParams.get("entry");
  const requestedFocusId = searchParams.get("focus");

  const queryParams = {
    tag_id: tagFilter ?? undefined,
    color_tag: colorTagFilter ?? undefined,
    page,
    page_size: 50,
    sort_by: sortBy,
    sort_order: sortOrder,
  } as const;

  const booksQuery = useQuery({
    queryKey: queryKeys.booksList(queryParams),
    queryFn: () => listBooks(queryParams),
  });
  const tagsQuery = useQuery({
    queryKey: queryKeys.tags,
    queryFn: listTags,
  });
  const {
    clearSelection,
    enterBatchMode,
    exitBatchMode,
    isBatchMode,
    isSelected,
    selectedCount,
    selectedIds,
    toggleSelection,
  } = useBatchSelection({
    pageLabel: "Books",
    resetDeps: [tagFilter, colorTagFilter, sortBy, sortOrder, page],
  });
  const { applyColorTag, applyTag, isApplyingColorTag, isApplyingTag } = useBatchOrganizeActions({
    onSuccess: clearSelection,
  });

  const totalPages = booksQuery.data ? Math.max(1, Math.ceil(booksQuery.data.total / booksQuery.data.page_size)) : 1;
  const showLoadingSkeleton = booksQuery.isLoading && !booksQuery.data;
  const hasNoRecognizedBooks = booksQuery.data !== undefined && booksQuery.data.total === 0;
  const hasNoCurrentPageResults = booksQuery.data !== undefined && booksQuery.data.total > 0 && booksQuery.data.items.length === 0;
  const hasActiveBookFilters = tagFilter !== null || colorTagFilter !== null;
  const selectedTagLabel = useMemo(() => {
    if (tagFilter === null) {
      return null;
    }
    const matchedTag = tagsQuery.data?.items.find((tag) => tag.id === tagFilter);
    return matchedTag?.name ?? `Tag #${tagFilter}`;
  }, [tagFilter, tagsQuery.data]);
  const filterSummary = useMemo(() => {
    const sortLabel = sortBy === "modified_at" ? "Modified" : sortBy === "name" ? "Name" : "Discovered";
    const parts: string[] = [];
    if (selectedTagLabel) {
      parts.push(`Tag: ${selectedTagLabel}`);
    }
    if (colorTagFilter) {
      parts.push(`Color: ${formatColorTagLabel(colorTagFilter)}`);
    }
    parts.push(`Sorted by ${sortLabel} (${sortOrder === "desc" ? "Descending" : "Ascending"})`);
    return parts.length > 0 ? `Showing: ${parts.join(" · ")}` : "Showing all recognized ebook entries.";
  }, [colorTagFilter, selectedTagLabel, sortBy, sortOrder]);
  const entryCopy = useMemo(() => {
    if (entry === "recent") {
      return "Opened from Recent so you can continue organizing this ebook inside the Books subset surface.";
    }
    if (entry === "tags") {
      return "Opened from Tags so you can review the ebook subset attached to the current tag.";
    }
    if (entry === "collections") {
      return "Opened from Collections so you can browse the ebook subset represented by the selected retrieval.";
    }
    if (entry === "details") {
      return "Opened from shared details so you can re-find this ebook inside the Books subset surface.";
    }
    return null;
  }, [entry]);

  useEffect(() => {
    const nextTagId = searchParams.get("tag_id");
    const nextColorTag = searchParams.get("color_tag");
    const parsedTagId = nextTagId ? Number(nextTagId) : null;
    setTagFilter(Number.isInteger(parsedTagId) && parsedTagId !== null && parsedTagId > 0 ? parsedTagId : null);
    setColorTagFilter(
      nextColorTag === "red" ||
      nextColorTag === "yellow" ||
      nextColorTag === "green" ||
      nextColorTag === "blue" ||
      nextColorTag === "purple"
        ? nextColorTag
        : null,
    );
    setPage(1);
  }, [searchParams]);

  useEffect(() => {
    if (!requestedFocusId || !booksQuery.data) {
      return;
    }

    const focusedItem = booksQuery.data.items.find((item) => String(item.id) === requestedFocusId);
    if (focusedItem) {
      selectItem(String(focusedItem.id));
    }
  }, [booksQuery.data, requestedFocusId, selectItem]);

  const clearBookFilters = () => {
    setTagFilter(null);
    setColorTagFilter(null);
    setPage(1);
    setSearchParams({});
  };

  const saveCurrentBookFiltersAsCollection = () => {
    const params = new URLSearchParams({
      prefill_file_type: "document",
      entry: "books",
    });
    const defaultNameParts: string[] = [];
    if (selectedTagLabel) {
      params.set("prefill_tag_id", String(tagFilter));
      defaultNameParts.push(selectedTagLabel);
    }
    if (colorTagFilter) {
      params.set("prefill_color_tag", colorTagFilter);
      defaultNameParts.push(formatColorTagLabel(colorTagFilter));
    }
    params.set("prefill_name", defaultNameParts.length > 0 ? `${defaultNameParts.join(" ")} Books` : "Books Collection");
    navigate(`/collections?${params.toString()}`);
  };

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Library subset browsing</span>
        <h3>Recognized ebook files</h3>
        <p>Select a card to load shared details. Double-click a card to open the indexed file.</p>
      </div>

      <div className="files-toolbar">
        <label className="field-stack files-toolbar__field">
          <span>Sort by</span>
          <select
            className="select-input"
            value={sortBy}
            onChange={(event) => {
              setSortBy(event.target.value as FileListSortBy);
              setPage(1);
            }}
          >
            <option value="modified_at">Modified</option>
            <option value="name">Name</option>
            <option value="discovered_at">Discovered</option>
          </select>
        </label>
        <label className="field-stack files-toolbar__field">
          <span>Order</span>
          <select
            className="select-input"
            value={sortOrder}
          onChange={(event) => {
            setSortOrder(event.target.value as FileListSortOrder);
            setPage(1);
          }}
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </label>
        <label className="field-stack files-toolbar__field">
          <span>Tag</span>
          <select
            className="select-input"
            value={tagFilter === null ? "all" : String(tagFilter)}
            onChange={(event) => {
              const nextValue = event.target.value;
              setTagFilter(nextValue === "all" ? null : Number(nextValue));
              setPage(1);
            }}
            disabled={tagsQuery.isLoading || tagsQuery.isError}
          >
            <option value="all">All tags</option>
            {tagsQuery.data?.items.map((tag) => (
              <option key={tag.id} value={tag.id}>
                {tag.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack files-toolbar__field">
          <span>Color</span>
          <select
            className="select-input"
            value={colorTagFilter ?? "all"}
            onChange={(event) => {
              const nextValue = event.target.value;
              setColorTagFilter(nextValue === "all" ? null : (nextValue as ColorTagValue));
              setPage(1);
            }}
          >
            <option value="all">All colors</option>
            {COLOR_TAG_OPTIONS.map((colorTag) => (
              <option key={colorTag} value={colorTag}>
                {formatColorTagLabel(colorTag)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {entryCopy ? <div className="context-flow-note">{entryCopy}</div> : null}

      <div className="books-filter-summary">
        <p>{hasActiveBookFilters ? filterSummary : `Showing all recognized ebook entries. Sorted by ${sortBy === "modified_at" ? "Modified" : sortBy === "name" ? "Name" : "Discovered"} (${sortOrder === "desc" ? "Descending" : "Ascending"}).`}</p>
        <div className="books-filter-summary__actions">
          {!isBatchMode ? (
            <button className="ghost-button" type="button" onClick={enterBatchMode}>
              Batch organize
            </button>
          ) : null}
          {hasActiveBookFilters ? (
            <>
              <button className="ghost-button" type="button" onClick={clearBookFilters}>
                Clear filters
              </button>
              <button className="ghost-button" type="button" onClick={saveCurrentBookFiltersAsCollection}>
                Save current book filters as collection
              </button>
            </>
          ) : null}
        </div>
      </div>

      {isBatchMode ? (
        <BatchActionBar
          isApplyingColorTag={isApplyingColorTag}
          isApplyingTag={isApplyingTag}
          onApplyColorTag={(colorTag) => applyColorTag(selectedIds, colorTag)}
          onApplyTag={(name) => applyTag(selectedIds, name)}
          onClearSelection={clearSelection}
          onExitBatchMode={exitBatchMode}
          selectedCount={selectedCount}
        />
      ) : null}

      <div className="files-meta-row">
        <p>Showing recognized .epub and .pdf files from the active indexed library with book-first visual cues and the shared workbench actions.</p>
        {booksQuery.data ? <span>{booksQuery.data.total} ebook files</span> : null}
      </div>

      {showLoadingSkeleton ? (
        <div className="books-library-grid books-library-grid--loading" aria-label="Loading books library">
          {Array.from({ length: 8 }, (_, index) => (
            <BooksCardSkeleton key={index} />
          ))}
        </div>
      ) : null}

      {booksQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Books listing failed</strong>
          <p>{booksQuery.error.message}</p>
        </div>
      ) : null}

      {hasNoRecognizedBooks ? (
        <div className="future-frame">
          No recognized ebook files are available yet. Add a source and run a scan to populate this subset surface.
        </div>
      ) : null}

      {hasNoCurrentPageResults ? (
        <div className="future-frame">
          No recognized ebook files match the current page and filters. Move between pages or change sorting to keep
          browsing.
        </div>
      ) : null}

      {booksQuery.data && booksQuery.data.items.length > 0 ? (
        <>
          <div className="books-library-grid">
            {booksQuery.data.items.map((item) => (
              <BooksLibraryCard
                key={item.id}
                bookFormat={item.book_format}
                displayTitle={item.display_title}
                isFavorite={item.is_favorite}
                isBatchMode={isBatchMode}
                modifiedAt={item.modified_at}
                path={item.path}
                rating={item.rating}
                selected={isBatchMode ? isSelected(item.id) : selectedItemId === String(item.id)}
                sizeBytes={item.size_bytes}
                onSelect={() => {
                  if (isBatchMode) {
                    toggleSelection(item.id);
                    return;
                  }
                  selectItem(String(item.id));
                }}
              />
            ))}
          </div>
          <div className="files-pager">
            <button
              className="secondary-button"
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={page <= 1}
            >
              Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              disabled={page >= totalPages}
            >
              Next
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}
