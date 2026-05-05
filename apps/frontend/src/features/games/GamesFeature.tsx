import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t, useLocale } from "../../shared/text";
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
import type { GameFormat } from "../../entities/game/types";


function formatBytes(value: number | null): string {
  return value === null ? t("common.states.sizeUnavailable") : `${value.toLocaleString()} bytes`;
}

function formatGameFormat(value: GameFormat): string {
  return value.toUpperCase();
}

function formatModifiedAt(value: string): string {
  return new Date(value).toLocaleString();
}

function buildGameEntryLabel(value: GameFormat): string {
  return value === "lnk" ? t("features.games.shortcutEntry") : t("features.games.executableEntry");
}

function formatStatusLabel(value: FileStatusValue): string {
  return value === "playing"
    ? t("features.games.statuses.playing")
    : value === "completed"
      ? t("features.games.statuses.completed")
      : t("features.games.statuses.shelved");
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

function countByFormat(items: Array<{ game_format: GameFormat }>, format: GameFormat): number {
  return items.filter((item) => item.game_format === format).length;
}

function countWithStatus(items: Array<{ status: FileStatusValue | null }>): number {
  return items.filter((item) => item.status !== null).length;
}

function GamesLibraryRow({
  displayTitle,
  gameFormat,
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
  gameFormat: GameFormat;
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
      className={`compact-library-table__row${selected ? " compact-library-table__row--selected" : ""}`}
      type="button"
      onClick={onSelect}
      onDoubleClick={() => {
        if (isBatchMode) {
          return;
        }
        void handleDoubleClick();
      }}
    >
      <span className="compact-library-table__name-cell">
        <span className={`compact-library-table__format-mark compact-library-table__format-mark--game-${gameFormat}`} aria-hidden="true">
          <span>{formatGameFormat(gameFormat)}</span>
        </span>
        <span className="compact-library-table__name-copy">
          <strong title={displayTitle}>{displayTitle}</strong>
          <span title={path}>{path}</span>
        </span>
      </span>
      <span className="compact-library-table__type-cell">
        <span className="status-pill">{formatGameFormat(gameFormat)}</span>
      </span>
      <span className="compact-library-table__kind-cell" title={t("features.games.gameEntryFile", { format: formatGameFormat(gameFormat) })}>
        <strong>{buildGameEntryLabel(gameFormat)}</strong>
        <span>{t("features.games.gameEntryFile", { format: formatGameFormat(gameFormat) })}</span>
      </span>
      <span className="compact-library-table__status-cell">
        {status ? <span className="status-pill games-card__status-pill">{formatStatusLabel(status)}</span> : <span className="compact-library-table__signals-empty">{t("common.states.none")}</span>}
      </span>
      <span className="compact-library-table__modified-cell">{formatModifiedAt(modifiedAt)}</span>
      <span className="compact-library-table__size-cell">{formatBytes(sizeBytes)}</span>
      <span className="compact-library-table__signals-cell">
        {isFavorite ? <span className="status-pill status-pill--favorite">{t("common.favorites.favorite")}</span> : null}
        {rating !== null ? <span className="status-pill status-pill--rating">★ {rating}</span> : null}
        {isBatchMode && selected ? <span className="status-pill">{t("common.states.selected")}</span> : null}
        {!isFavorite && rating === null && !(isBatchMode && selected) ? (
          <span className="compact-library-table__signals-empty">{t("common.states.none")}</span>
        ) : null}
      </span>
    </button>
  );
}

function GamesRowSkeleton() {
  return (
    <div className="compact-library-table__row compact-library-table__row--skeleton" aria-hidden="true">
      <span className="compact-library-skeleton-line compact-library-skeleton-line--title" />
      <span className="compact-library-skeleton-pill" />
      <span className="compact-library-skeleton-line compact-library-skeleton-line--short" />
      <span className="compact-library-skeleton-pill" />
      <span className="compact-library-skeleton-line" />
      <span className="compact-library-skeleton-line compact-library-skeleton-line--short" />
      <span className="compact-library-skeleton-pill" />
    </div>
  );
}


export function GamesFeature() {
  const { locale } = useLocale();
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const navigate = useNavigate();
  const gameStatusOptions: Array<{ label: string; value: FileStatusValue | "all" }> = [
    { label: t("features.games.statuses.all"), value: "all" },
    { label: t("features.games.statuses.playing"), value: "playing" },
    { label: t("features.games.statuses.completed"), value: "completed" },
    { label: t("features.games.statuses.shelved"), value: "shelved" },
  ];
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
    pageLabel: t("pages.games.title"),
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
    return matchedTag?.name ?? t("common.labels.tagId", { id: tagFilter });
  }, [locale, tagFilter, tagsQuery.data]);
  const showEmptyState = (gamesQuery.data?.total === 0) && !hasActiveStatusFilter && !hasActiveRetrievalFilters;
  const showNoResultsState =
    ((hasActiveStatusFilter || hasActiveRetrievalFilters) && (gamesQuery.data?.total ?? 0) === 0) ||
    ((gamesQuery.data?.total ?? 0) > 0 && (gamesQuery.data?.items.length ?? 0) === 0);
  const currentItems = gamesQuery.data?.items ?? [];
  const summaryStats = useMemo(
    () => ({
      total: gamesQuery.data?.total ?? 0,
      visible: currentItems.length,
      exe: countByFormat(currentItems, "exe"),
      lnk: countByFormat(currentItems, "lnk"),
      status: countWithStatus(currentItems),
      filters: [hasActiveStatusFilter ? statusFilter : null, tagFilter, colorTagFilter].filter(Boolean).length,
    }),
    [colorTagFilter, currentItems, gamesQuery.data?.total, hasActiveStatusFilter, statusFilter, tagFilter],
  );
  const entryCopy = useMemo(() => {
    if (entry === "tags") {
      return t("features.games.entry.tags");
    }
    if (entry === "collections") {
      return t("features.games.entry.collections");
    }
    if (entry === "recent") {
      return t("features.games.entry.recent");
    }
    if (entry === "details") {
      return t("features.games.entry.details");
    }
    return null;
  }, [entry, locale]);
  const filterSummary = useMemo(() => {
    const sortLabel =
      sortBy === "modified_at" ? t("common.sortBy.modified") : sortBy === "name" ? t("common.sortBy.name") : t("common.sortBy.discovered");
    const parts: string[] = [];
    if (hasActiveStatusFilter) {
      parts.push(`${t("common.labels.status")}: ${formatStatusLabel(statusFilter)}`);
    }
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
    return parts.length > 1
      ? t("features.games.showingSummary", { summary: parts.join(" · ") })
      : t("features.games.allSummary", { summary: parts[0] });
  }, [colorTagFilter, hasActiveStatusFilter, locale, selectedTagLabel, sortBy, sortOrder, statusFilter]);

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
    params.set(
      "prefill_name",
      defaultNameParts.length > 0
        ? `${defaultNameParts.join(" ")} ${t("features.games.collectionPrefill.base")}`
        : t("features.games.collectionPrefill.default"),
    );
    navigate(`/collections?${params.toString()}`);
  };

  return (
    <section className="feature-shell compact-library">
      <div className="feature-header compact-library__header">
        <span className="page-header__eyebrow">{t("features.games.eyebrow")}</span>
        <h3>{t("features.games.title")}</h3>
        <p>{t("features.games.description")}</p>
      </div>

      <div className="compact-summary-strip" aria-label={t("features.games.summary.ariaLabel")}>
        <div className="compact-summary-strip__item">
          <span>{t("features.games.summary.total")}</span>
          <strong>{summaryStats.total.toLocaleString()}</strong>
        </div>
        <div className="compact-summary-strip__item">
          <span>{t("features.games.summary.visible")}</span>
          <strong>{summaryStats.visible.toLocaleString()}</strong>
        </div>
        <div className="compact-summary-strip__item">
          <span>{t("features.games.summary.exe")}</span>
          <strong>{summaryStats.exe.toLocaleString()}</strong>
        </div>
        <div className="compact-summary-strip__item">
          <span>{t("features.games.summary.lnk")}</span>
          <strong>{summaryStats.lnk.toLocaleString()}</strong>
        </div>
        <div className="compact-summary-strip__item">
          <span>{t("features.games.summary.status")}</span>
          <strong>{summaryStats.status.toLocaleString()}</strong>
        </div>
        <div className="compact-summary-strip__item">
          <span>{t("features.games.summary.filters")}</span>
          <strong>{summaryStats.filters.toLocaleString()}</strong>
        </div>
      </div>

      <div className="compact-action-bar">
        <div className="compact-action-bar__copy">
          <span className="page-header__eyebrow">{t("features.games.quickActions.eyebrow")}</span>
          <p>{t("features.games.quickActions.description")}</p>
        </div>
        <div className="compact-action-bar__actions">
          {!isBatchMode ? (
            <button className="ghost-button" type="button" onClick={enterBatchMode}>
              {t("common.actions.batchOrganize")}
            </button>
          ) : null}
          <button className="ghost-button" type="button" onClick={() => navigate("/search")}>
            {t("features.games.quickActions.search")}
          </button>
          <button className="ghost-button" type="button" onClick={() => navigate("/settings")}>
            {t("features.games.quickActions.sources")}
          </button>
          {hasActiveStatusFilter || hasActiveRetrievalFilters ? (
            <button className="ghost-button" type="button" onClick={clearFilters}>
              {t("common.actions.clearFilters")}
            </button>
          ) : null}
          {hasActiveRetrievalFilters ? (
            <button className="ghost-button" type="button" onClick={saveCurrentGameFiltersAsCollection}>
              {t("features.games.saveFiltersAsCollection")}
            </button>
          ) : null}
        </div>
      </div>

      <div className="subset-filter-block compact-filter-block">
        {entryCopy ? <div className="context-flow-note">{entryCopy}</div> : null}

        <div className="files-toolbar compact-filter-toolbar">
          <label className="field-stack files-toolbar__field compact-filter-toolbar__field">
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
          <label className="field-stack files-toolbar__field compact-filter-toolbar__field">
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
          <label className="field-stack files-toolbar__field compact-filter-toolbar__field">
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
          <label className="field-stack files-toolbar__field compact-filter-toolbar__field">
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
              {(["red", "yellow", "green", "blue", "purple"] as ColorTagValue[]).map((colorTag) => (
                <option key={colorTag} value={colorTag}>
                  {formatColorTagLabel(colorTag)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="games-status-switch" aria-label={t("features.games.statusFilterAria")}>
          {gameStatusOptions.map((option) => (
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
        <div className="games-filter-summary compact-filter-summary">
          <p>{filterSummary}</p>
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
        <p>{t("features.games.meta")}</p>
        {gamesQuery.data ? <span>{t("common.labels.gameEntryFiles", { count: gamesQuery.data.total })}</span> : null}
      </div>

      {showLoadingSkeleton ? (
        <div className="compact-library-table compact-library-table--loading" aria-label={t("features.games.loadingAria")}>
          {Array.from({ length: 8 }, (_, index) => (
            <GamesRowSkeleton key={index} />
          ))}
        </div>
      ) : null}

      {gamesQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.games.failedTitle")}</strong>
          <p>{gamesQuery.error.message}</p>
        </div>
      ) : null}

      {showEmptyState ? (
        <div className="future-frame">{t("features.games.empty")}</div>
      ) : null}

      {showNoResultsState ? (
        <div className="future-frame">{t("features.games.noResults")}</div>
      ) : null}

      {gamesQuery.data && gamesQuery.data.items.length > 0 ? (
        <>
          <div className="compact-library-table compact-library-table--games" role="table" aria-label={t("features.games.table.ariaLabel")}>
            <div className="compact-library-table__header" role="row">
              <span>{t("features.games.table.name")}</span>
              <span>{t("features.games.table.type")}</span>
              <span>{t("features.games.table.kind")}</span>
              <span>{t("features.games.table.status")}</span>
              <span>{t("features.games.table.modified")}</span>
              <span>{t("features.games.table.size")}</span>
              <span>{t("features.games.table.signals")}</span>
            </div>
            {gamesQuery.data.items.map((item) => (
              <GamesLibraryRow
                key={item.id}
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
