import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t, useLocale } from "../../shared/text";
import { BatchActionBar } from "../batch-organize/BatchActionBar";
import { useBatchOrganizeActions } from "../batch-organize/useBatchOrganizeActions";
import { useBatchSelection } from "../batch-organize/useBatchSelection";
import type { ColorTagValue, FileListSortBy, FileListSortOrder } from "../../entities/file/types";
import type { MediaViewScope } from "../../entities/media/types";
import { getFileThumbnailUrl } from "../../services/api/fileDetailsApi";
import {
  hasDesktopOpenActionsBridge,
  normalizeIndexedFilePath,
  openIndexedFile,
} from "../../services/desktop/openActions";
import { listMediaLibrary } from "../../services/api/mediaLibraryApi";
import { listTags } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? t("common.states.sizeUnavailable") : `${value.toLocaleString()} bytes`;
}

function getColorTagLabel(value: ColorTagValue | "all"): string {
  if (value === "all") {
    return t("common.colors.all");
  }
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

function buildCollectionPrefillName({
  viewScope,
  selectedTagName,
  selectedColorTag,
}: {
  viewScope: MediaViewScope;
  selectedTagName: string | null;
  selectedColorTag: ColorTagValue | "all";
}): string {
  const parts = [t("pages.media.title")];

  if (viewScope === "image") {
    parts.push(t("features.media.scopes.image"));
  } else if (viewScope === "video") {
    parts.push(t("features.media.scopes.video"));
  }

  if (selectedTagName) {
    parts.push(selectedTagName);
  }

  if (selectedColorTag !== "all") {
    parts.push(getColorTagLabel(selectedColorTag));
  }

  return parts.join(" · ");
}

function MediaPoster({
  fileId,
  fileType,
  name,
}: {
  fileId: number;
  fileType: "image" | "video";
  name: string;
}) {
  const [thumbnailFailed, setThumbnailFailed] = useState(false);
  const [thumbnailLoaded, setThumbnailLoaded] = useState(false);

  if (thumbnailFailed) {
      return (
        <div className={`media-card__poster ${fileType === "video" ? "media-card__poster--video" : ""}`}>
          <div className="media-card__poster-copy">
            <strong>
              {fileType === "image"
                ? t("features.media.previewFallback.imageTitle")
                : t("features.media.previewFallback.videoTitle")}
            </strong>
            <span>
              {fileType === "image"
                ? t("features.media.previewFallback.imageHint")
                : t("features.media.previewFallback.videoHint")}
            </span>
          </div>
        </div>
      );
  }

  return (
    <div className={`media-card__poster media-card__poster--image${fileType === "video" ? " media-card__poster--video-thumb" : ""}`}>
      {!thumbnailLoaded ? <div className="media-card__poster-skeleton" aria-hidden="true" /> : null}
      <img
        className={`media-card__thumbnail${thumbnailLoaded ? " media-card__thumbnail--ready" : ""}`}
        src={getFileThumbnailUrl(fileId)}
        alt={t("features.media.thumbnailAlt", { name })}
        loading="lazy"
        onError={() => setThumbnailFailed(true)}
        onLoad={() => setThumbnailLoaded(true)}
      />
    </div>
  );
}

function MediaCardSkeleton() {
  return (
    <div className="media-card media-card--skeleton" aria-hidden="true">
      <div className="media-card__poster media-card__poster--skeleton" />
      <div className="media-card__body media-card__body--skeleton">
        <span className="media-card__skeleton-line media-card__skeleton-line--title" />
        <span className="media-card__skeleton-line media-card__skeleton-line--path" />
        <span className="media-card__skeleton-line media-card__skeleton-line--path-short" />
      </div>
      <div className="media-card__meta media-card__meta--skeleton">
        <span className="media-card__skeleton-pill" />
        <span className="media-card__skeleton-pill" />
        <span className="media-card__skeleton-pill" />
      </div>
    </div>
  );
}

function MediaLibraryCard({
  fileId,
  fileType,
  isFavorite,
  isBatchMode,
  modifiedAt,
  name,
  path,
  rating,
  selected,
  sizeBytes,
  onSelect,
}: {
  fileId: number;
  fileType: "image" | "video";
  isFavorite: boolean;
  isBatchMode: boolean;
  modifiedAt: string;
  name: string;
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
      className={`media-card${selected ? " media-card--selected" : ""}`}
      type="button"
      onClick={onSelect}
      onDoubleClick={() => {
        if (isBatchMode) {
          return;
        }
        void handleDoubleClick();
      }}
    >
      <MediaPoster fileId={fileId} fileType={fileType} name={name} />
      <div className="media-card__body">
        <strong title={name}>{name}</strong>
        <p title={path}>{path}</p>
      </div>
      <div className="media-card__meta">
        <span className="status-pill">{fileType}</span>
        <span className="status-pill">{formatBytes(sizeBytes)}</span>
        <span className="status-pill">{new Date(modifiedAt).toLocaleString()}</span>
        {isFavorite ? <span className="status-pill status-pill--favorite">{t("common.favorites.favorite")}</span> : null}
        {rating !== null ? <span className="status-pill status-pill--rating">★ {rating}</span> : null}
        {isBatchMode && selected ? <span className="status-pill">{t("common.states.selected")}</span> : null}
      </div>
    </button>
  );
}


export function MediaLibraryFeature() {
  const { locale } = useLocale();
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const navigate = useNavigate();
  const viewScopeOptions: Array<{ label: string; value: MediaViewScope }> = [
    { label: t("features.media.scopes.all"), value: "all" },
    { label: t("features.media.scopes.image"), value: "image" },
    { label: t("features.media.scopes.video"), value: "video" },
  ];
  const colorTagOptions: Array<{ label: string; value: ColorTagValue | "all" }> = [
    { label: t("common.colors.all"), value: "all" },
    { label: t("common.colors.red"), value: "red" },
    { label: t("common.colors.yellow"), value: "yellow" },
    { label: t("common.colors.green"), value: "green" },
    { label: t("common.colors.blue"), value: "blue" },
    { label: t("common.colors.purple"), value: "purple" },
  ];
  const [searchParams, setSearchParams] = useSearchParams();
  const [viewScope, setViewScope] = useState<MediaViewScope>("all");
  const [selectedTagId, setSelectedTagId] = useState("all");
  const [selectedColorTag, setSelectedColorTag] = useState<ColorTagValue | "all">("all");
  const [sortBy, setSortBy] = useState<FileListSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");
  const [page, setPage] = useState(1);
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
    pageLabel: t("shell.topbar.pages.media"),
    resetDeps: [viewScope, selectedTagId, selectedColorTag, sortBy, sortOrder, page],
  });
  const { applyColorTag, applyTag, isApplyingColorTag, isApplyingTag } = useBatchOrganizeActions({
    onSuccess: clearSelection,
  });
  const entry = searchParams.get("entry");
  const requestedFocusId = searchParams.get("focus");

  const queryParams = {
    view_scope: viewScope,
    tag_id: selectedTagId === "all" ? undefined : Number(selectedTagId),
    color_tag: selectedColorTag === "all" ? undefined : selectedColorTag,
    page,
    page_size: 50,
    sort_by: sortBy,
    sort_order: sortOrder,
  } as const;

  const mediaQuery = useQuery({
    queryKey: queryKeys.mediaLibrary(queryParams),
    queryFn: () => listMediaLibrary(queryParams),
  });

  const totalPages = mediaQuery.data ? Math.max(1, Math.ceil(mediaQuery.data.total / mediaQuery.data.page_size)) : 1;
  const showLoadingSkeleton = mediaQuery.isLoading && !mediaQuery.data;
  const showEmptyState = mediaQuery.data?.total === 0;
  const showNoResultsState = (mediaQuery.data?.total ?? 0) > 0 && (mediaQuery.data?.items.length ?? 0) === 0;
  const selectedTagName =
    selectedTagId === "all"
      ? null
      : tagsQuery.data?.items.find((tag) => String(tag.id) === selectedTagId)?.name ?? t("common.labels.tag");
  const hasActiveFilters =
    viewScope !== "all" ||
    selectedTagId !== "all" ||
    selectedColorTag !== "all" ||
    sortBy !== "modified_at" ||
    sortOrder !== "desc";
  const filterSummary = hasActiveFilters
    ? [
        `${t("common.labels.scope")}: ${viewScopeOptions.find((option) => option.value === viewScope)?.label ?? t("features.media.scopes.all")}`,
        selectedTagName ? `${t("common.labels.tag")}: ${selectedTagName}` : null,
        selectedColorTag !== "all" ? `${t("common.labels.color")}: ${getColorTagLabel(selectedColorTag)}` : null,
        t("common.labels.sortedBy", {
          sort: sortBy === "modified_at" ? t("common.sortBy.modified") : sortBy === "name" ? t("common.sortBy.name") : t("common.sortBy.discovered"),
          order: sortOrder === "desc" ? t("common.sortOrder.descending") : t("common.sortOrder.ascending"),
        }),
      ]
        .filter(Boolean)
        .join(" · ")
    : t("features.media.summaryAll");
  const entryCopy = useMemo(() => {
    if (entry === "recent") {
      return t("features.media.entry.recent");
    }
    if (entry === "tags") {
      return t("features.media.entry.tags");
    }
    if (entry === "collections") {
      return t("features.media.entry.collections");
    }
    if (entry === "details") {
      return t("features.media.entry.details");
    }
    return null;
  }, [entry, locale]);
  const saveCollectionHref = useMemo(() => {
    if (!hasActiveFilters) {
      return null;
    }

    const nextParams = new URLSearchParams();
    nextParams.set(
      "prefill_name",
      buildCollectionPrefillName({
        viewScope,
        selectedTagName,
        selectedColorTag,
      }),
    );
    if (viewScope !== "all") {
      nextParams.set("prefill_file_type", viewScope);
    }
    if (selectedTagId !== "all") {
      nextParams.set("prefill_tag_id", selectedTagId);
    }
    if (selectedColorTag !== "all") {
      nextParams.set("prefill_color_tag", selectedColorTag);
    }
    nextParams.set("entry", "media");
    return `/collections?${nextParams.toString()}`;
  }, [hasActiveFilters, locale, selectedColorTag, selectedTagId, selectedTagName, viewScope]);

  useEffect(() => {
    const nextViewScope = searchParams.get("view_scope");
    const nextTagId = searchParams.get("tag_id");
    const nextColorTag = searchParams.get("color_tag");

    setViewScope(nextViewScope === "image" || nextViewScope === "video" ? nextViewScope : "all");
    setSelectedTagId(nextTagId ?? "all");
    setSelectedColorTag(
      nextColorTag === "red" ||
        nextColorTag === "yellow" ||
        nextColorTag === "green" ||
        nextColorTag === "blue" ||
        nextColorTag === "purple"
        ? nextColorTag
        : "all",
    );
    setSortBy("modified_at");
    setSortOrder("desc");
    setPage(1);
  }, [searchParams]);

  useEffect(() => {
    if (!requestedFocusId || !mediaQuery.data) {
      return;
    }

    const focusedItem = mediaQuery.data.items.find((item) => String(item.id) === requestedFocusId);
    if (focusedItem) {
      selectItem(String(focusedItem.id));
    }
  }, [mediaQuery.data, requestedFocusId, selectItem]);

  const resetFilters = () => {
    setViewScope("all");
    setSelectedTagId("all");
    setSelectedColorTag("all");
    setSortBy("modified_at");
    setSortOrder("desc");
    setPage(1);
    setSearchParams({});
  };

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">{t("features.media.eyebrow")}</span>
        <h3>{t("features.media.title")}</h3>
        <p>{t("features.media.description")}</p>
      </div>

      <div className="subset-filter-block">
        {entryCopy ? <div className="media-library-flow-note">{entryCopy}</div> : null}

        <div className="media-library-toolbar">
          <div className="field-stack media-library-toolbar__field media-library-toolbar__field--wide">
            <span>{t("common.labels.scope")}</span>
            <div className="media-library-scope-switch" aria-label={t("features.media.scopeAria")}>
                  {viewScopeOptions.map((option) => (
                <button
                  key={option.value}
                  className={`secondary-button media-library-scope-button${viewScope === option.value ? " media-library-scope-button--selected" : ""}`}
                  type="button"
                  onClick={() => {
                    setViewScope(option.value);
                    setPage(1);
                  }}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
          <label className="field-stack media-library-toolbar__field">
            <span>{t("common.labels.tag")}</span>
            <select
              className="select-input"
              value={selectedTagId}
              onChange={(event) => {
                setSelectedTagId(event.target.value);
                setPage(1);
              }}
              disabled={tagsQuery.isLoading || tagsQuery.error instanceof Error}
            >
              <option value="all">
                {tagsQuery.error instanceof Error ? t("common.tagFilters.unavailable") : t("common.tagFilters.all")}
              </option>
              {(tagsQuery.data?.items ?? []).map((tag) => (
                <option key={tag.id} value={tag.id}>
                  {tag.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack media-library-toolbar__field">
            <span>{t("common.labels.color")}</span>
            <select
              className="select-input"
              value={selectedColorTag}
              onChange={(event) => {
                setSelectedColorTag(event.target.value as ColorTagValue | "all");
                setPage(1);
              }}
            >
              {colorTagOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack media-library-toolbar__field">
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
          <label className="field-stack media-library-toolbar__field">
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
        </div>
        <div className="media-library-filter-summary">
          <p>{filterSummary}</p>
          <div className="media-library-filter-summary__actions">
            {!isBatchMode ? (
              <button className="ghost-button" type="button" onClick={enterBatchMode}>
                {t("common.actions.batchOrganize")}
              </button>
            ) : null}
            {saveCollectionHref ? (
              <button
                className="ghost-button"
                type="button"
                onClick={() => {
                  navigate(saveCollectionHref);
                }}
              >
                {t("features.media.saveFiltersAsCollection")}
              </button>
            ) : null}
            {hasActiveFilters ? (
              <button className="ghost-button media-library-filter-summary__clear" type="button" onClick={resetFilters}>
                {t("common.actions.clearFilters")}
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

      <div className="media-library-meta-row">
        <p>
          {viewScope === "all"
            ? t("features.media.metaAll")
            : t("features.media.metaScoped", { scope: viewScope })}
        </p>
        {mediaQuery.data ? <span>{t("common.labels.mediaItems", { count: mediaQuery.data.total })}</span> : null}
      </div>

      {showLoadingSkeleton ? (
        <div className="media-library-grid media-library-grid--loading" aria-label={t("features.media.loadingAria")}>
          {Array.from({ length: 8 }, (_, index) => (
            <MediaCardSkeleton key={index} />
          ))}
        </div>
      ) : null}

      {mediaQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.media.failedTitle")}</strong>
          <p>{mediaQuery.error.message}</p>
        </div>
      ) : null}

      {tagsQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.search.tagsUnavailableTitle")}</strong>
          <p>{tagsQuery.error.message}</p>
        </div>
      ) : null}

      {showEmptyState ? (
        <div className="future-frame">{t("features.media.empty")}</div>
      ) : null}

      {showNoResultsState ? (
        <div className="future-frame">{t("features.media.noResults")}</div>
      ) : null}

      {mediaQuery.data && mediaQuery.data.items.length > 0 ? (
        <>
          <div className="media-library-grid">
            {mediaQuery.data.items.map((item) => (
              <MediaLibraryCard
                key={item.id}
                fileId={item.id}
                fileType={item.file_type}
                isFavorite={item.is_favorite}
                isBatchMode={isBatchMode}
                modifiedAt={item.modified_at}
                name={item.name}
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
          <div className="media-library-pager">
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
