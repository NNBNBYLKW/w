import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t, useLocale } from "../../shared/text";
import { AssetIconGrid, ViewModeToggle, useViewMode, type AssetIconCardItem } from "../../shared/ui/view-mode";
import { useRetryingThumbnail, useThumbnailWarmup } from "../../shared/ui/thumbnail";
import { BatchActionBar } from "../batch-organize/BatchActionBar";
import { useBatchOrganizeActions } from "../batch-organize/useBatchOrganizeActions";
import { useBatchSelection } from "../batch-organize/useBatchSelection";
import type { ColorTagValue, FileKind, FileListSortBy, FileListSortOrder, FileStatusValue, StorageStateFilter } from "../../entities/file/types";
import {
  hasDesktopOpenActionsBridge,
  normalizeIndexedFilePath,
  openIndexedFile,
} from "../../services/desktop/openActions";
import { getFileThumbnailUrl } from "../../services/api/fileDetailsApi";
import { listGames } from "../../services/api/gamesApi";
import { listTags } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";
import type { GameFormat } from "../../entities/game/types";

const IMAGE_THUMBNAIL_EXTENSIONS = new Set(["avif", "gif", "jpeg", "jpg", "png", "webp"]);
const VIDEO_THUMBNAIL_EXTENSIONS = new Set(["avi", "mkv", "mov", "mp4", "webm"]);
const ARCHIVE_EXTENSIONS = new Set(["7z", "gz", "rar", "tar", "zip"]);
const DISK_IMAGE_EXTENSIONS = new Set(["bin", "chd", "cue", "cso", "iso"]);
const ROM_EXTENSIONS = new Set(["3ds", "gba", "gbc", "nds", "nes"]);
const INSTALLER_EXTENSIONS = new Set(["appx", "msi", "msix"]);

type GameDisplayInfo = {
  entryLabel: string;
  hint: string;
  mark: string;
  markTone: "game";
  thumbnailCapable: boolean;
  thumbnailFit?: "cover" | "contain";
  typeLabel: string;
};

function normalizeGameExtension(value: string): string {
  return value.trim().replace(/^\.+/, "").toLowerCase();
}

function getGameFormatModifier(value: string): string {
  return normalizeGameExtension(value).replace(/[^a-z0-9_-]/g, "-") || "generic";
}

function formatBytes(value: number | null): string {
  return value === null ? t("common.states.sizeUnavailable") : `${value.toLocaleString()} bytes`;
}

function formatModifiedAt(value: string): string {
  return new Date(value).toLocaleString();
}

function buildGameDisplayInfo({ fileKind, format }: { fileKind: FileKind; format: GameFormat }): GameDisplayInfo {
  const extension = normalizeGameExtension(format);
  const typeLabel = extension ? extension.toUpperCase() : "FILE";
  const isImageThumbnail = fileKind === "image" && IMAGE_THUMBNAIL_EXTENSIONS.has(extension);
  const isVideoThumbnail = fileKind === "video" && VIDEO_THUMBNAIL_EXTENSIONS.has(extension);
  const isExeThumbnail = fileKind === "executable" && extension === "exe";
  const isPdfThumbnail = (fileKind === "document" || fileKind === "ebook") && extension === "pdf";
  const thumbnailCapable = isImageThumbnail || isVideoThumbnail || isExeThumbnail || isPdfThumbnail;

  if (extension === "lnk" || fileKind === "shortcut") {
    return {
      entryLabel: t("features.games.shortcutEntry"),
      hint: t("features.games.gameEntryFile", { format: typeLabel }),
      mark: "LNK",
      markTone: "game",
      thumbnailCapable: false,
      typeLabel,
    };
  }
  if (isExeThumbnail) {
    return {
      entryLabel: t("features.games.executableEntry"),
      hint: t("features.games.gameEntryFile", { format: typeLabel }),
      mark: "EXE",
      markTone: "game",
      thumbnailCapable,
      thumbnailFit: "contain",
      typeLabel,
    };
  }
  if (isPdfThumbnail) {
    return {
      entryLabel: t("features.games.genericEntry"),
      hint: t("features.games.gameEntryFile", { format: typeLabel }),
      mark: "PDF",
      markTone: "game",
      thumbnailCapable,
      thumbnailFit: "contain",
      typeLabel,
    };
  }
  if (isImageThumbnail || isVideoThumbnail) {
    return {
      entryLabel: t("features.games.genericEntry"),
      hint: t("features.games.gameEntryFile", { format: typeLabel }),
      mark: isImageThumbnail ? "IMG" : "VID",
      markTone: "game",
      thumbnailCapable,
      typeLabel,
    };
  }
  if (fileKind === "archive" || ARCHIVE_EXTENSIONS.has(extension)) {
    return {
      entryLabel: t("features.games.genericEntry"),
      hint: t("features.games.gameEntryFile", { format: typeLabel }),
      mark: extension === "7z" ? "7Z" : typeLabel.slice(0, 3),
      markTone: "game",
      thumbnailCapable: false,
      typeLabel,
    };
  }
  if (DISK_IMAGE_EXTENSIONS.has(extension)) {
    return {
      entryLabel: t("features.games.genericEntry"),
      hint: t("features.games.gameEntryFile", { format: typeLabel }),
      mark: typeLabel.slice(0, 3),
      markTone: "game",
      thumbnailCapable: false,
      typeLabel,
    };
  }
  if (ROM_EXTENSIONS.has(extension)) {
    return {
      entryLabel: t("features.games.genericEntry"),
      hint: t("features.games.gameEntryFile", { format: typeLabel }),
      mark: typeLabel.slice(0, 3),
      markTone: "game",
      thumbnailCapable: false,
      typeLabel,
    };
  }
  if (fileKind === "installer" || INSTALLER_EXTENSIONS.has(extension)) {
    return {
      entryLabel: t("features.games.genericEntry"),
      hint: t("features.games.gameEntryFile", { format: typeLabel }),
      mark: typeLabel.slice(0, 4),
      markTone: "game",
      thumbnailCapable: false,
      typeLabel,
    };
  }
  if (fileKind === "document" || fileKind === "ebook") {
    return {
      entryLabel: t("features.games.genericEntry"),
      hint: t("features.games.gameEntryFile", { format: typeLabel }),
      mark: typeLabel.slice(0, 4),
      markTone: "game",
      thumbnailCapable: false,
      typeLabel,
    };
  }

  return {
    entryLabel: t("features.games.genericEntry"),
    hint: t("features.games.gameEntryFile", { format: typeLabel }),
    mark: typeLabel.slice(0, 4),
    markTone: "game",
    thumbnailCapable: false,
    typeLabel,
  };
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
  displayInfo,
  displayTitle,
  fileId,
  gameFormat,
  isFavorite,
  isBatchMode,
  modifiedAt,
  path,
  rating,
  selected,
  sizeBytes,
  status,
  thumbnailDisabled,
  thumbnailRefreshToken,
  onThumbnailLoaded,
  onSelect,
}: {
  displayInfo: GameDisplayInfo;
  displayTitle: string;
  fileId: number;
  gameFormat: GameFormat;
  isFavorite: boolean;
  isBatchMode: boolean;
  modifiedAt: string;
  path: string;
  rating: number | null;
  selected: boolean;
  sizeBytes: number | null;
  status: FileStatusValue | null;
  thumbnailDisabled?: boolean;
  thumbnailRefreshToken?: number;
  onThumbnailLoaded?: () => void;
  onSelect: () => void;
}) {
  const hasDesktopOpenActions = hasDesktopOpenActionsBridge();
  const thumbnail = useRetryingThumbnail<HTMLSpanElement>({
    enabled: displayInfo.thumbnailCapable && !thumbnailDisabled,
    onLoad: onThumbnailLoaded,
    refreshToken: thumbnailRefreshToken,
    thumbnailUrl: displayInfo.thumbnailCapable ? getFileThumbnailUrl(fileId) : undefined,
  });

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
        <span
          className={`compact-library-table__format-mark compact-library-table__format-mark--game-${getGameFormatModifier(gameFormat)}`}
          aria-hidden="true"
          ref={thumbnail.ref}
        >
          {thumbnail.shouldRenderImage ? (
            <img
              className={`compact-library-table__thumb-image${displayInfo.thumbnailFit === "contain" ? " compact-library-table__thumb-image--contain" : ""} compact-library-table__thumb-image--ready`}
              src={thumbnail.imageSrc}
              alt=""
              width={44}
              height={44}
              loading="lazy"
              onError={thumbnail.onError}
              onLoad={thumbnail.onLoad}
            />
          ) : (
            <span>{displayInfo.mark}</span>
          )}
        </span>
        <span className="compact-library-table__name-copy">
          <strong title={displayTitle}>{displayTitle}</strong>
          <span title={path}>{path}</span>
        </span>
      </span>
      <span className="compact-library-table__type-cell">
        <span className="status-pill">{displayInfo.typeLabel}</span>
      </span>
      <span className="compact-library-table__kind-cell" title={displayInfo.hint}>
        <strong>{displayInfo.entryLabel}</strong>
        <span>{displayInfo.hint}</span>
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
  const { viewMode, setViewMode } = useViewMode("games");
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
  const [storageState, setStorageState] = useState<StorageStateFilter | "all">("all");
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
  const { applyColorTag, applyPlacement, applyTag, isApplyingColorTag, isApplyingPlacement, isApplyingTag } = useBatchOrganizeActions({
    onSuccess: clearSelection,
  });

  const queryParams = {
    status: statusFilter === "all" ? undefined : statusFilter,
    tag_id: tagFilter ?? undefined,
    color_tag: colorTagFilter ?? undefined,
    storage_state: storageState === "all" ? undefined : storageState,
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
  const iconItems = useMemo<AssetIconCardItem[]>(
    () =>
      currentItems.map((item) => {
        const displayInfo = buildGameDisplayInfo({
          fileKind: item.file_kind,
          format: item.game_format,
        });
        return {
          id: item.id,
          title: item.display_title,
          path: item.path,
          typeLabel: displayInfo.typeLabel,
          meta: `${displayInfo.entryLabel} · ${formatBytes(item.size_bytes)}`,
          mark: displayInfo.mark,
          markTone: displayInfo.markTone,
          thumbnailAlt: item.display_title,
          thumbnailFit: displayInfo.thumbnailFit,
          thumbnailUrl: displayInfo.thumbnailCapable ? getFileThumbnailUrl(item.id) : undefined,
          selected: isBatchMode ? isSelected(item.id) : selectedItemId === String(item.id),
          signals: [
            item.status ? formatStatusLabel(item.status) : null,
            item.is_favorite ? t("common.favorites.favorite") : null,
            item.rating !== null ? `★ ${item.rating}` : null,
            isBatchMode && isSelected(item.id) ? t("common.states.selected") : null,
          ].filter((value): value is string => value !== null),
        };
      }),
    [currentItems, isBatchMode, isSelected, selectedItemId],
  );
  const thumbnailWarmup = useThumbnailWarmup(iconItems.filter((item) => item.thumbnailUrl).map((item) => item.id));

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
    <section className="feature-shell compact-library browse-surface browse-surface--games">
      <div className="feature-header compact-library__header browse-surface__header">
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
            <span>{t("common.labels.storageScope")}</span>
            <select
              className="select-input"
              value={storageState}
              onChange={(event) => {
                setStorageState(event.target.value as StorageStateFilter | "all");
                setPage(1);
              }}
            >
              <option value="all">{t("common.storageScope.all")}</option>
              <option value="external">{t("common.storageScope.external")}</option>
              <option value="inbox">{t("common.storageScope.inbox")}</option>
              <option value="managed">{t("common.storageScope.managed")}</option>
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
          <div className="compact-filter-toolbar__view-mode">
            <ViewModeToggle value={viewMode} onChange={setViewMode} />
          </div>
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
            isApplyingPlacement={isApplyingPlacement}
            isApplyingTag={isApplyingTag}
            onApplyColorTag={(colorTag) => applyColorTag(selectedIds, colorTag)}
            onApplyPlacement={(manualPlacement) => applyPlacement(selectedIds, manualPlacement)}
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
          {viewMode === "icons" ? (
            <AssetIconGrid
              ariaLabel={t("features.games.table.ariaLabel")}
              items={iconItems}
              getThumbnailRefreshToken={(item) => thumbnailWarmup.getRefreshToken(item.id)}
              isThumbnailDisabled={(item) => !item.thumbnailUrl || thumbnailWarmup.isThumbnailDisabled(item.id)}
              onThumbnailLoaded={(item) => thumbnailWarmup.markLoaded(item.id)}
              onSelect={(item) => {
                if (isBatchMode) {
                  toggleSelection(item.id);
                  return;
                }
                selectItem(String(item.id));
              }}
              onOpen={(iconItem) => {
                if (isBatchMode) {
                  return;
                }
                const matchedItem = gamesQuery.data.items.find((item) => item.id === iconItem.id);
                const normalizedPath = normalizeIndexedFilePath(matchedItem?.path);
                if (!normalizedPath || !hasDesktopOpenActionsBridge()) {
                  return;
                }
                void openIndexedFile(normalizedPath);
              }}
            />
          ) : (
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
              {gamesQuery.data.items.map((item) => {
                const displayInfo = buildGameDisplayInfo({
                  fileKind: item.file_kind,
                  format: item.game_format,
                });
                return (
                  <GamesLibraryRow
                    key={item.id}
                    displayInfo={displayInfo}
                    displayTitle={item.display_title}
                    fileId={item.id}
                    gameFormat={item.game_format}
                    isFavorite={item.is_favorite}
                    isBatchMode={isBatchMode}
                    modifiedAt={item.modified_at}
                    path={item.path}
                    rating={item.rating}
                    selected={isBatchMode ? isSelected(item.id) : selectedItemId === String(item.id)}
                    sizeBytes={item.size_bytes}
                    status={item.status}
                    thumbnailDisabled={!displayInfo.thumbnailCapable || thumbnailWarmup.isThumbnailDisabled(item.id)}
                    thumbnailRefreshToken={thumbnailWarmup.getRefreshToken(item.id)}
                    onThumbnailLoaded={() => thumbnailWarmup.markLoaded(item.id)}
                    onSelect={() => {
                      if (isBatchMode) {
                        toggleSelection(item.id);
                        return;
                      }
                      selectItem(String(item.id));
                    }}
                  />
                );
              })}
            </div>
          )}
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
