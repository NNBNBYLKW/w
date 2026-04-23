import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { BatchActionBar } from "../batch-organize/BatchActionBar";
import { useBatchOrganizeActions } from "../batch-organize/useBatchOrganizeActions";
import { useBatchSelection } from "../batch-organize/useBatchSelection";
import type { ColorTagValue, FileListSortBy, FileListSortOrder, FileStatusValue } from "../../entities/file/types";
import {
  hasDesktopOpenActionsBridge,
  normalizeIndexedFilePath,
  openIndexedFile,
} from "../../services/desktop/openActions";
import { listGames } from "../../services/api/gamesApi";
import { listTags } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}

function formatGameFormat(value: "exe" | "lnk"): string {
  return value.toUpperCase();
}

function formatModifiedAt(value: string): string {
  return new Date(value).toLocaleString();
}

function buildGameEntryLabel(value: "exe" | "lnk"): string {
  return value === "lnk" ? "Shortcut entry" : "Executable entry";
}

function formatStatusLabel(value: FileStatusValue): string {
  return value === "playing" ? "Playing" : value === "completed" ? "Completed" : "Shelved";
}

function formatColorTagLabel(value: ColorTagValue): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

const GAME_STATUS_OPTIONS: Array<{ label: string; value: FileStatusValue | "all" }> = [
  { label: "All", value: "all" },
  { label: "Playing", value: "playing" },
  { label: "Completed", value: "completed" },
  { label: "Shelved", value: "shelved" },
];

const GAMES_ENTRY_COPY: Record<string, string> = {
  details: "Opened from shared details so you can keep re-finding this game entry inside the current subset surface.",
};

function GamesLibraryCard({
  displayTitle,
  gameFormat,
  id,
  isFavorite,
  isBatchMode,
  modifiedAt,
  path,
  rating,
  selected,
  sizeBytes,
  status,
  onSelect,
}: {
  displayTitle: string;
  gameFormat: "exe" | "lnk";
  id: number;
  isFavorite: boolean;
  isBatchMode: boolean;
  modifiedAt: string;
  path: string;
  rating: number | null;
  selected: boolean;
  sizeBytes: number | null;
  status: FileStatusValue | null;
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
      className={`games-card${selected ? " games-card--selected" : ""}`}
      type="button"
      onClick={onSelect}
      onDoubleClick={() => {
        if (isBatchMode) {
          return;
        }
        void handleDoubleClick();
      }}
    >
      <div className={`games-card__poster games-card__poster--${gameFormat}`}>
        <div className="games-card__poster-copy">
          <span className="games-card__poster-icon" aria-hidden="true">
            {gameFormat === "lnk" ? "↗" : "▶"}
          </span>
          <strong>{buildGameEntryLabel(gameFormat)}</strong>
          <span>{formatGameFormat(gameFormat)} game entry file</span>
        </div>
      </div>
      <div className="games-card__body">
        <strong title={displayTitle}>{displayTitle}</strong>
        <p title={path}>{path}</p>
      </div>
      <div className="games-card__meta">
        <span className="status-pill">{formatGameFormat(gameFormat)}</span>
        <span className="status-pill">{formatBytes(sizeBytes)}</span>
        <span className="status-pill">{formatModifiedAt(modifiedAt)}</span>
        {status ? <span className="status-pill games-card__status-pill">{formatStatusLabel(status)}</span> : null}
        {isFavorite ? <span className="status-pill status-pill--favorite">★ Favorite</span> : null}
        {rating !== null ? <span className="status-pill status-pill--rating">★ {rating}</span> : null}
        {isBatchMode && selected ? <span className="status-pill">Selected</span> : null}
      </div>
      <span className="games-card__hint">Single-click for shared details. Double-click to open the indexed file.</span>
      <span className="games-card__id" aria-hidden="true">
        #{id}
      </span>
    </button>
  );
}

function GamesCardSkeleton() {
  return (
    <div className="games-card games-card--skeleton" aria-hidden="true">
      <div className="games-card__poster games-card__poster--skeleton" />
      <div className="games-card__body games-card__body--skeleton">
        <span className="games-card__skeleton-line games-card__skeleton-line--title" />
        <span className="games-card__skeleton-line games-card__skeleton-line--path" />
        <span className="games-card__skeleton-line games-card__skeleton-line--path-short" />
      </div>
      <div className="games-card__meta games-card__meta--skeleton">
        <span className="games-card__skeleton-pill" />
        <span className="games-card__skeleton-pill" />
        <span className="games-card__skeleton-pill" />
      </div>
    </div>
  );
}


export function GamesFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const entry = searchParams.get("entry");
  const requestedFocusId = searchParams.get("focus");
  const [sortBy, setSortBy] = useState<FileListSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");
  const [statusFilter, setStatusFilter] = useState<FileStatusValue | "all">("all");
  const [tagFilter, setTagFilter] = useState<number | null>(null);
  const [colorTagFilter, setColorTagFilter] = useState<ColorTagValue | null>(null);
  const [page, setPage] = useState(1);
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
    pageLabel: "Games",
    resetDeps: [sortBy, sortOrder, statusFilter, tagFilter, colorTagFilter, page],
  });
  const { applyColorTag, applyTag, isApplyingColorTag, isApplyingTag } = useBatchOrganizeActions({
    onSuccess: clearSelection,
  });

  const queryParams = {
    status: statusFilter === "all" ? undefined : statusFilter,
    tag_id: tagFilter ?? undefined,
    color_tag: colorTagFilter ?? undefined,
    page,
    page_size: 50,
    sort_by: sortBy,
    sort_order: sortOrder,
  } as const;

  const gamesQuery = useQuery({
    queryKey: queryKeys.gamesList(queryParams),
    queryFn: () => listGames(queryParams),
  });
  const tagsQuery = useQuery({
    queryKey: queryKeys.tags,
    queryFn: listTags,
  });

  const totalPages = gamesQuery.data ? Math.max(1, Math.ceil(gamesQuery.data.total / gamesQuery.data.page_size)) : 1;
  const showLoadingSkeleton = gamesQuery.isLoading && !gamesQuery.data;
  const hasActiveStatusFilter = statusFilter !== "all";
  const hasActiveRetrievalFilters = tagFilter !== null || colorTagFilter !== null;
  const selectedTagLabel = useMemo(() => {
    if (tagFilter === null) {
      return null;
    }
    const matchedTag = tagsQuery.data?.items.find((tag) => tag.id === tagFilter);
    return matchedTag?.name ?? `Tag #${tagFilter}`;
  }, [tagFilter, tagsQuery.data]);
  const showEmptyState = (gamesQuery.data?.total === 0) && !hasActiveStatusFilter && !hasActiveRetrievalFilters;
  const showNoResultsState =
    ((hasActiveStatusFilter || hasActiveRetrievalFilters) && (gamesQuery.data?.total ?? 0) === 0) ||
    ((gamesQuery.data?.total ?? 0) > 0 && (gamesQuery.data?.items.length ?? 0) === 0);
  const entryCopy = useMemo(() => {
    if (entry === "tags") {
      return "Opened from Tags so you can review the games subset attached to the current tag.";
    }
    if (entry === "collections") {
      return "Opened from Collections so you can browse the games subset represented by the selected retrieval.";
    }
    if (entry === "recent") {
      return "Opened from Recent so you can continue organizing this game entry inside the Games subset surface.";
    }
    return entry ? GAMES_ENTRY_COPY[entry] : null;
  }, [entry]);
  const filterSummary = useMemo(() => {
    const sortLabel = sortBy === "modified_at" ? "Modified" : sortBy === "name" ? "Name" : "Discovered";
    const parts: string[] = [];
    if (hasActiveStatusFilter) {
      parts.push(`Status: ${formatStatusLabel(statusFilter)}`);
    }
    if (selectedTagLabel) {
      parts.push(`Tag: ${selectedTagLabel}`);
    }
    if (colorTagFilter) {
      parts.push(`Color: ${formatColorTagLabel(colorTagFilter)}`);
    }
    parts.push(`Sorted by ${sortLabel} (${sortOrder === "desc" ? "Descending" : "Ascending"})`);
    return parts.length > 1
      ? `Showing: ${parts.join(" · ")}`
      : `Showing all recognized game-entry files. ${parts[0]}`;
  }, [colorTagFilter, hasActiveStatusFilter, selectedTagLabel, sortBy, sortOrder, statusFilter]);

  useEffect(() => {
    const nextStatus = searchParams.get("status");
    const nextTagId = searchParams.get("tag_id");
    const nextColorTag = searchParams.get("color_tag");
    const parsedTagId = nextTagId ? Number(nextTagId) : null;
    setStatusFilter(nextStatus === "playing" || nextStatus === "completed" || nextStatus === "shelved" ? nextStatus : "all");
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
    setSortBy("modified_at");
    setSortOrder("desc");
    setPage(1);
  }, [searchParams]);

  useEffect(() => {
    if (!requestedFocusId || !gamesQuery.data) {
      return;
    }

    const focusedItem = gamesQuery.data.items.find((item) => String(item.id) === requestedFocusId);
    if (focusedItem) {
      selectItem(String(focusedItem.id));
    }
  }, [gamesQuery.data, requestedFocusId, selectItem]);

  const clearFilters = () => {
    setStatusFilter("all");
    setTagFilter(null);
    setColorTagFilter(null);
    setPage(1);
    setSearchParams({});
  };

  const saveCurrentGameFiltersAsCollection = () => {
    const params = new URLSearchParams({
      entry: "games",
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
    params.set("prefill_name", defaultNameParts.length > 0 ? `${defaultNameParts.join(" ")} Games` : "Games Collection");
    navigate(`/collections?${params.toString()}`);
  };

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Library subset browsing</span>
        <h3>Recognized game-entry files</h3>
        <p>Select a card to load shared details. Double-click a card to open the indexed file.</p>
      </div>

      {entryCopy ? <div className="context-flow-note">{entryCopy}</div> : null}

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
            {(["red", "yellow", "green", "blue", "purple"] as ColorTagValue[]).map((colorTag) => (
              <option key={colorTag} value={colorTag}>
                {formatColorTagLabel(colorTag)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="games-status-switch" aria-label="Games status filter">
        {GAME_STATUS_OPTIONS.map((option) => (
          <button
            key={option.value}
            className={`secondary-button games-status-button${statusFilter === option.value ? " games-status-button--selected" : ""}`}
            type="button"
            onClick={() => {
              setStatusFilter(option.value);
              setPage(1);
            }}
          >
            {option.label}
          </button>
        ))}
      </div>
      <div className="games-filter-summary">
        <p>{filterSummary}</p>
        <div className="software-filter-summary__actions">
          {!isBatchMode ? (
            <button className="ghost-button" type="button" onClick={enterBatchMode}>
              Batch organize
            </button>
          ) : null}
          {hasActiveStatusFilter || hasActiveRetrievalFilters ? (
            <button className="ghost-button" type="button" onClick={clearFilters}>
              Clear filters
            </button>
          ) : null}
          {hasActiveRetrievalFilters ? (
            <button className="ghost-button" type="button" onClick={saveCurrentGameFiltersAsCollection}>
              Save current game filters as collection
            </button>
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
        <p>Showing recognized game-entry files from the active indexed library without expanding into a launcher platform.</p>
        {gamesQuery.data ? <span>{gamesQuery.data.total} game-entry files</span> : null}
      </div>

      {showLoadingSkeleton ? (
        <div className="games-library-grid games-library-grid--loading" aria-label="Loading games library">
          {Array.from({ length: 8 }, (_, index) => (
            <GamesCardSkeleton key={index} />
          ))}
        </div>
      ) : null}

      {gamesQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Games listing failed</strong>
          <p>{gamesQuery.error.message}</p>
        </div>
      ) : null}

      {showEmptyState ? (
        <div className="future-frame">
          No recognized game-entry files are available yet. Scan a source with .lnk files or narrow game-entry .exe
          files to populate this subset surface.
        </div>
      ) : null}

      {showNoResultsState ? (
        <div className="future-frame">
          No recognized game-entry files match the current filters on this page. Move between pages, clear the filters,
          or change sorting to keep browsing.
        </div>
      ) : null}

      {gamesQuery.data && gamesQuery.data.items.length > 0 ? (
        <>
          <div className="games-library-grid">
            {gamesQuery.data.items.map((item) => (
              <GamesLibraryCard
                key={item.id}
                id={item.id}
                displayTitle={item.display_title}
                gameFormat={item.game_format}
                isFavorite={item.is_favorite}
                isBatchMode={isBatchMode}
                modifiedAt={item.modified_at}
                path={item.path}
                rating={item.rating}
                selected={isBatchMode ? isSelected(item.id) : selectedItemId === String(item.id)}
                sizeBytes={item.size_bytes}
                status={item.status}
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
