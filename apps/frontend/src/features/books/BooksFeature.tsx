import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t, useLocale } from "../../shared/text";
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
  return value === null ? t("common.states.sizeUnavailable") : `${value.toLocaleString()} bytes`;
}

function formatBookFormat(value: BookFormat): string {
  return value.toUpperCase();
}

function formatModifiedAt(value: string): string {
  return new Date(value).toLocaleString();
}

function buildBookEntryLabel(value: BookFormat): string {
  return value === "epub" ? t("features.books.ebookEntry") : t("features.books.documentEdition");
}

function buildBookFormatCopy(value: BookFormat): string {
  return value === "epub" ? t("features.books.epubCopy") : t("features.books.pdfCopy");
}

function buildBookFormatHint(value: BookFormat): string {
  return value === "epub" ? t("features.books.epubHint") : t("features.books.pdfHint");
}

function formatColorTagLabel(value: ColorTagValue): string {
  if (value === "red") {
    return t("common.colors.red");
  }
  if (value === "yellow") {
    return t("common.colors.yellow");
  }
  if (value === "green") {
    return t("common.colors.green");
  }
  if (value === "blue") {
    return t("common.colors.blue");
  }
  return t("common.colors.purple");
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
        {isFavorite ? <span className="status-pill status-pill--favorite">{t("common.favorites.favorite")}</span> : null}
        {rating !== null ? <span className="status-pill status-pill--rating">★ {rating}</span> : null}
        {isBatchMode && selected ? <span className="status-pill">{t("common.states.selected")}</span> : null}
      </div>
      <span className="books-card__hint">{t("features.books.clickHint")}</span>
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
  const { locale } = useLocale();
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
    pageLabel: t("pages.books.title"),
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
    return matchedTag?.name ?? t("common.labels.tagId", { id: tagFilter });
  }, [locale, tagFilter, tagsQuery.data]);
  const filterSummary = useMemo(() => {
    const sortLabel =
      sortBy === "modified_at" ? t("common.sortBy.modified") : sortBy === "name" ? t("common.sortBy.name") : t("common.sortBy.discovered");
    const parts: string[] = [];
    if (selectedTagLabel) {
      parts.push(`${t("common.labels.tag")}: ${selectedTagLabel}`);
    }
    if (colorTagFilter) {
      parts.push(`${t("common.labels.color")}: ${formatColorTagLabel(colorTagFilter)}`);
    }
    parts.push(
      t("common.labels.sortedBy", {
        sort: sortLabel,
        order: sortOrder === "desc" ? t("common.sortOrder.descending") : t("common.sortOrder.ascending"),
      }),
    );
    return parts.length > 0 ? t("features.books.filterSummary", { summary: parts.join(" · ") }) : t("features.books.showingAllEntries");
  }, [colorTagFilter, locale, selectedTagLabel, sortBy, sortOrder]);
  const entryCopy = useMemo(() => {
    if (entry === "recent") {
      return t("features.books.entry.recent");
    }
    if (entry === "tags") {
      return t("features.books.entry.tags");
    }
    if (entry === "collections") {
      return t("features.books.entry.collections");
    }
    if (entry === "details") {
      return t("features.books.entry.details");
    }
    return null;
  }, [entry, locale]);

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
    params.set(
      "prefill_name",
      defaultNameParts.length > 0
        ? `${defaultNameParts.join(" ")} ${t("features.books.collectionPrefill.base")}`
        : t("features.books.collectionPrefill.default"),
    );
    navigate(`/collections?${params.toString()}`);
  };

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">{t("features.books.eyebrow")}</span>
        <h3>{t("features.books.title")}</h3>
        <p>{t("features.books.description")}</p>
      </div>

      <div className="subset-filter-block">
        <div className="files-toolbar">
          <label className="field-stack files-toolbar__field">
            <span>{t("common.labels.sortBy")}</span>
            <select
              className="select-input"
              value={sortBy}
              onChange={(event) => {
                setSortBy(event.target.value as FileListSortBy);
                setPage(1);
              }}
            >
              <option value="modified_at">{t("common.sortBy.modified")}</option>
              <option value="name">{t("common.sortBy.name")}</option>
              <option value="discovered_at">{t("common.sortBy.discovered")}</option>
            </select>
          </label>
          <label className="field-stack files-toolbar__field">
            <span>{t("common.labels.order")}</span>
            <select
              className="select-input"
              value={sortOrder}
              onChange={(event) => {
                setSortOrder(event.target.value as FileListSortOrder);
                setPage(1);
              }}
            >
              <option value="desc">{t("common.sortOrder.descending")}</option>
              <option value="asc">{t("common.sortOrder.ascending")}</option>
            </select>
          </label>
          <label className="field-stack files-toolbar__field">
            <span>{t("common.labels.tag")}</span>
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
              <option value="all">{t("common.tagFilters.all")}</option>
              {tagsQuery.data?.items.map((tag) => (
                <option key={tag.id} value={tag.id}>
                  {tag.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack files-toolbar__field">
            <span>{t("common.labels.color")}</span>
            <select
              className="select-input"
              value={colorTagFilter ?? "all"}
              onChange={(event) => {
                const nextValue = event.target.value;
                setColorTagFilter(nextValue === "all" ? null : (nextValue as ColorTagValue));
                setPage(1);
              }}
            >
              <option value="all">{t("common.colors.all")}</option>
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
          <p>
            {hasActiveBookFilters
              ? filterSummary
              : t("features.books.pageAllSummary", {
                  order: sortOrder === "desc" ? t("common.sortOrder.descending") : t("common.sortOrder.ascending"),
                  sort:
                    sortBy === "modified_at"
                      ? t("common.sortBy.modified")
                      : sortBy === "name"
                        ? t("common.sortBy.name")
                        : t("common.sortBy.discovered"),
                })}
          </p>
          <div className="books-filter-summary__actions">
            {!isBatchMode ? (
              <button className="ghost-button" type="button" onClick={enterBatchMode}>
                {t("common.actions.batchOrganize")}
              </button>
            ) : null}
            {hasActiveBookFilters ? (
              <>
                <button className="ghost-button" type="button" onClick={clearBookFilters}>
                  {t("common.actions.clearFilters")}
                </button>
                <button className="ghost-button" type="button" onClick={saveCurrentBookFiltersAsCollection}>
                  {t("features.books.saveFiltersAsCollection")}
                </button>
              </>
            ) : null}
          </div>
        </div>
      </div>

      {isBatchMode ? (
        <div className="subset-batch-block">
          <BatchActionBar
            isApplyingColorTag={isApplyingColorTag}
            isApplyingTag={isApplyingTag}
            onApplyColorTag={(colorTag) => applyColorTag(selectedIds, colorTag)}
            onApplyTag={(name) => applyTag(selectedIds, name)}
            onClearSelection={clearSelection}
            onExitBatchMode={exitBatchMode}
            selectedCount={selectedCount}
          />
        </div>
      ) : null}

      <div className="files-meta-row">
        <p>{t("features.books.meta")}</p>
        {booksQuery.data ? <span>{t("common.labels.ebookFiles", { count: booksQuery.data.total })}</span> : null}
      </div>

      {showLoadingSkeleton ? (
        <div className="books-library-grid books-library-grid--loading" aria-label={t("features.books.loadingAria")}>
          {Array.from({ length: 8 }, (_, index) => (
            <BooksCardSkeleton key={index} />
          ))}
        </div>
      ) : null}

      {booksQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.books.failedTitle")}</strong>
          <p>{booksQuery.error.message}</p>
        </div>
      ) : null}

      {hasNoRecognizedBooks ? (
        <div className="future-frame">{t("features.books.empty")}</div>
      ) : null}

      {hasNoCurrentPageResults ? (
        <div className="future-frame">{t("features.books.noResults")}</div>
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
              {t("common.actions.previous")}
            </button>
            <span>{t("common.labels.page", { page, total: totalPages })}</span>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              disabled={page >= totalPages}
            >
              {t("common.actions.next")}
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}
