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


function formatBytes(value: number | null): string {
  return value === null ? t("common.states.sizeUnavailable") : `${value.toLocaleString()} bytes`;
}

function formatGameFormat(value: "exe" | "lnk"): string {
  return value.toUpperCase();
}

function formatModifiedAt(value: string): string {
  return new Date(value).toLocaleString();
}

function buildGameEntryLabel(value: "exe" | "lnk"): string {
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
          <span>{t("features.games.gameEntryFile", { format: formatGameFormat(gameFormat) })}</span>
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
        {isFavorite ? <span className="status-pill status-pill--favorite">{t("common.favorites.favorite")}</span> : null}
        {rating !== null ? <span className="status-pill status-pill--rating">★ {rating}</span> : null}
        {isBatchMode && selected ? <span className="status-pill">{t("common.states.selected")}</span> : null}
      </div>
      <span className="games-card__hint">{t("features.games.clickHint")}</span>
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
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">{t("features.games.eyebrow")}</span>
        <h3>{t("features.games.title")}</h3>
        <p>{t("features.games.description")}</p>
      </div>

      <div className="subset-filter-block">
        {entryCopy ? <div className="context-flow-note">{entryCopy}</div> : null}

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
        <div className="games-filter-summary">
          <p>{filterSummary}</p>
          <div className="software-filter-summary__actions">
            {!isBatchMode ? (
              <button className="ghost-button" type="button" onClick={enterBatchMode}>
                {t("common.actions.batchOrganize")}
              </button>
            ) : null}
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
        <div className="games-library-grid games-library-grid--loading" aria-label={t("features.games.loadingAria")}>
          {Array.from({ length: 8 }, (_, index) => (
            <GamesCardSkeleton key={index} />
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
