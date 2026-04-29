import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t, useLocale } from "../../shared/text";
import { BatchActionBar } from "../batch-organize/BatchActionBar";
import { useBatchOrganizeActions } from "../batch-organize/useBatchOrganizeActions";
import { useBatchSelection } from "../batch-organize/useBatchSelection";
import type { ColorTagValue, FileListSortBy, FileListSortOrder } from "../../entities/file/types";
import type { SoftwareFormat } from "../../entities/software/types";
import { listSoftware } from "../../services/api/softwareApi";
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

function formatSoftwareFormat(value: SoftwareFormat): string {
  return value.toUpperCase();
}

function formatModifiedAt(value: string): string {
  return new Date(value).toLocaleString();
}

function buildSoftwareEntryLabel(value: SoftwareFormat): string {
  if (value === "exe") {
    return t("features.software.entryLabels.exe");
  }
  if (value === "msi") {
    return t("features.software.entryLabels.msi");
  }
  return t("features.software.entryLabels.zip");
}

function buildSoftwareFormatHint(value: SoftwareFormat): string {
  if (value === "exe") {
    return t("features.software.hints.exe");
  }
  if (value === "msi") {
    return t("features.software.hints.msi");
  }
  return t("features.software.hints.zip");
}

function buildSoftwareFormatCopy(value: SoftwareFormat): string {
  if (value === "exe") {
    return t("features.software.copies.exe");
  }
  if (value === "msi") {
    return t("features.software.copies.msi");
  }
  return t("features.software.copies.zip");
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

function SoftwareLibraryCard({
  displayTitle,
  isFavorite,
  isBatchMode,
  modifiedAt,
  path,
  rating,
  selected,
  sizeBytes,
  softwareFormat,
  onSelect,
}: {
  displayTitle: string;
  isFavorite: boolean;
  isBatchMode: boolean;
  modifiedAt: string;
  path: string;
  rating: number | null;
  selected: boolean;
  sizeBytes: number | null;
  softwareFormat: SoftwareFormat;
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
      className={`software-card${selected ? " software-card--selected" : ""}`}
      type="button"
      onClick={onSelect}
      onDoubleClick={() => {
        if (isBatchMode) {
          return;
        }
        void handleDoubleClick();
      }}
    >
      <div className={`software-card__poster software-card__poster--${softwareFormat}`}>
        <div className="software-card__poster-copy">
          <span className="software-card__poster-eyebrow">{t("features.software.posterEyebrow")}</span>
          <span className="software-card__poster-icon" aria-hidden="true">
            {softwareFormat === "exe" ? "EXE" : softwareFormat === "msi" ? "MSI" : "ZIP"}
          </span>
          <strong>{buildSoftwareEntryLabel(softwareFormat)}</strong>
          <span>{buildSoftwareFormatHint(softwareFormat)}</span>
        </div>
      </div>
      <div className="software-card__body">
        <strong title={displayTitle}>{displayTitle}</strong>
        <span className={`software-card__entry-note software-card__entry-note--${softwareFormat}`}>
          {buildSoftwareFormatCopy(softwareFormat)}
        </span>
        <p title={path}>{path}</p>
      </div>
      <div className="software-card__meta">
        <span className="status-pill">{formatSoftwareFormat(softwareFormat)}</span>
        <span className="status-pill">{formatBytes(sizeBytes)}</span>
        <span className="status-pill">{formatModifiedAt(modifiedAt)}</span>
        {isFavorite ? <span className="status-pill status-pill--favorite">{t("common.favorites.favorite")}</span> : null}
        {rating !== null ? <span className="status-pill status-pill--rating">★ {rating}</span> : null}
        {isBatchMode && selected ? <span className="status-pill">{t("common.states.selected")}</span> : null}
      </div>
      <span className="software-card__hint">
        {t("features.software.clickHint")}
      </span>
    </button>
  );
}

function SoftwareCardSkeleton() {
  return (
    <div className="software-card software-card--skeleton" aria-hidden="true">
      <div className="software-card__poster software-card__poster--skeleton" />
      <div className="software-card__body software-card__body--skeleton">
        <span className="software-card__skeleton-line software-card__skeleton-line--title" />
        <span className="software-card__skeleton-line software-card__skeleton-line--path" />
        <span className="software-card__skeleton-line software-card__skeleton-line--path-short" />
      </div>
      <div className="software-card__meta software-card__meta--skeleton">
        <span className="software-card__skeleton-pill" />
        <span className="software-card__skeleton-pill" />
        <span className="software-card__skeleton-pill" />
      </div>
    </div>
  );
}


export function SoftwareFeature() {
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
    pageLabel: t("pages.software.title"),
    resetDeps: [tagFilter, colorTagFilter, sortBy, sortOrder, page],
  });
  const { applyColorTag, applyTag, isApplyingColorTag, isApplyingTag } = useBatchOrganizeActions({
    onSuccess: clearSelection,
  });

  const queryParams = {
    tag_id: tagFilter ?? undefined,
    color_tag: colorTagFilter ?? undefined,
    page,
    page_size: 50,
    sort_by: sortBy,
    sort_order: sortOrder,
  } as const;

  const softwareQuery = useQuery({
    queryKey: queryKeys.softwareList(queryParams),
    queryFn: () => listSoftware(queryParams),
  });
  const tagsQuery = useQuery({
    queryKey: queryKeys.tags,
    queryFn: listTags,
  });

  const totalPages = softwareQuery.data ? Math.max(1, Math.ceil(softwareQuery.data.total / softwareQuery.data.page_size)) : 1;
  const showLoadingSkeleton = softwareQuery.isLoading && !softwareQuery.data;
  const showEmptyState = softwareQuery.data?.total === 0;
  const showNoResultsState = (softwareQuery.data?.total ?? 0) > 0 && (softwareQuery.data?.items.length ?? 0) === 0;
  const hasActiveSoftwareFilters = tagFilter !== null || colorTagFilter !== null;
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
    return parts.length > 0 ? t("features.software.showingSummary", { summary: parts.join(" · ") }) : "";
  }, [colorTagFilter, locale, selectedTagLabel, sortBy, sortOrder]);
  const entryCopy = useMemo(() => {
    if (entry === "recent") {
      return t("features.software.entry.recent");
    }
    if (entry === "tags") {
      return t("features.software.entry.tags");
    }
    if (entry === "collections") {
      return t("features.software.entry.collections");
    }
    if (entry === "details") {
      return t("features.software.entry.details");
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
    if (!requestedFocusId || !softwareQuery.data) {
      return;
    }

    const focusedItem = softwareQuery.data.items.find((item) => String(item.id) === requestedFocusId);
    if (focusedItem) {
      selectItem(String(focusedItem.id));
    }
  }, [requestedFocusId, selectItem, softwareQuery.data]);

  const clearSoftwareFilters = () => {
    setTagFilter(null);
    setColorTagFilter(null);
    setPage(1);
    setSearchParams({});
  };

  const saveCurrentSoftwareFiltersAsCollection = () => {
    const params = new URLSearchParams({
      entry: "software",
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
        ? `${defaultNameParts.join(" ")} ${t("features.software.collectionPrefill.base")}`
        : t("features.software.collectionPrefill.default"),
    );
    navigate(`/collections?${params.toString()}`);
  };

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">{t("features.software.eyebrow")}</span>
        <h3>{t("features.software.title")}</h3>
        <p>{t("features.software.description")}</p>
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

        <div className="software-filter-summary">
          <p>
            {hasActiveSoftwareFilters
              ? filterSummary
              : t("features.software.allSummary", {
                  order: sortOrder === "desc" ? t("common.sortOrder.descending") : t("common.sortOrder.ascending"),
                  sort:
                    sortBy === "modified_at"
                      ? t("common.sortBy.modified")
                      : sortBy === "name"
                        ? t("common.sortBy.name")
                        : t("common.sortBy.discovered"),
                })}
          </p>
          <div className="software-filter-summary__actions">
            {!isBatchMode ? (
              <button className="ghost-button" type="button" onClick={enterBatchMode}>
                {t("common.actions.batchOrganize")}
              </button>
            ) : null}
            {hasActiveSoftwareFilters ? (
              <>
                <button className="ghost-button" type="button" onClick={clearSoftwareFilters}>
                  {t("common.actions.clearFilters")}
                </button>
                <button className="ghost-button" type="button" onClick={saveCurrentSoftwareFiltersAsCollection}>
                  {t("features.software.saveFiltersAsCollection")}
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
        <p>{t("features.software.meta")}</p>
        {softwareQuery.data ? <span>{t("common.labels.softwareFiles", { count: softwareQuery.data.total })}</span> : null}
      </div>

      {showLoadingSkeleton ? (
        <div className="software-library-grid software-library-grid--loading" aria-label={t("features.software.loadingAria")}>
          {Array.from({ length: 8 }, (_, index) => (
            <SoftwareCardSkeleton key={index} />
          ))}
        </div>
      ) : null}

      {softwareQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.software.failedTitle")}</strong>
          <p>{softwareQuery.error.message}</p>
        </div>
      ) : null}

      {showEmptyState ? (
        <div className="future-frame">{t("features.software.empty")}</div>
      ) : null}

      {showNoResultsState ? (
        <div className="future-frame">{t("features.software.noResults")}</div>
      ) : null}

      {softwareQuery.data && softwareQuery.data.items.length > 0 ? (
        <>
          <div className="software-library-grid">
            {softwareQuery.data.items.map((item) => (
              <SoftwareLibraryCard
                key={item.id}
                displayTitle={item.display_title}
                isFavorite={item.is_favorite}
                isBatchMode={isBatchMode}
                modifiedAt={item.modified_at}
                path={item.path}
                rating={item.rating}
                selected={isBatchMode ? isSelected(item.id) : selectedItemId === String(item.id)}
                sizeBytes={item.size_bytes}
                softwareFormat={item.software_format}
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
