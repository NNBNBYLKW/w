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

function countByFormat(items: Array<{ software_format: SoftwareFormat }>, format: SoftwareFormat): number {
  return items.filter((item) => item.software_format === format).length;
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

function SoftwareLibraryRow({
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
  const entryLabel = buildSoftwareEntryLabel(softwareFormat);
  const formatCopy = buildSoftwareFormatCopy(softwareFormat);

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
      className={`software-table__row${selected ? " software-table__row--selected" : ""}`}
      type="button"
      onClick={onSelect}
      onDoubleClick={() => {
        if (isBatchMode) {
          return;
        }
        void handleDoubleClick();
      }}
    >
      <span className="software-table__name-cell">
        <span className={`software-table__format-mark software-table__format-mark--${softwareFormat}`} aria-hidden="true">
          <span>
            {softwareFormat === "exe" ? "EXE" : softwareFormat === "msi" ? "MSI" : "ZIP"}
          </span>
        </span>
        <span className="software-table__name-copy">
          <strong title={displayTitle}>{displayTitle}</strong>
          <span title={path}>{path}</span>
        </span>
      </span>
      <span className="software-table__type-cell">
        <span className="status-pill">{formatSoftwareFormat(softwareFormat)}</span>
      </span>
      <span className="software-table__kind-cell" title={buildSoftwareFormatHint(softwareFormat)}>
        <strong>{entryLabel}</strong>
        <span>{formatCopy}</span>
      </span>
      <span className="software-table__modified-cell">{formatModifiedAt(modifiedAt)}</span>
      <span className="software-table__size-cell">{formatBytes(sizeBytes)}</span>
      <span className="software-table__signals-cell">
        {isFavorite ? <span className="status-pill status-pill--favorite">{t("common.favorites.favorite")}</span> : null}
        {rating !== null ? <span className="status-pill status-pill--rating">★ {rating}</span> : null}
        {isBatchMode && selected ? <span className="status-pill">{t("common.states.selected")}</span> : null}
        {!isFavorite && rating === null && !(isBatchMode && selected) ? (
          <span className="software-table__signals-empty">{t("common.states.none")}</span>
        ) : null}
      </span>
    </button>
  );
}

function SoftwareRowSkeleton() {
  return (
    <div className="software-table__row software-table__row--skeleton" aria-hidden="true">
      <span className="software-card__skeleton-line software-card__skeleton-line--title" />
      <span className="software-card__skeleton-pill" />
      <span className="software-card__skeleton-line software-card__skeleton-line--path-short" />
      <span className="software-card__skeleton-line" />
      <span className="software-card__skeleton-line software-card__skeleton-line--path-short" />
      <span className="software-card__skeleton-pill" />
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
  const currentItems = softwareQuery.data?.items ?? [];
  const summaryStats = useMemo(
    () => ({
      total: softwareQuery.data?.total ?? 0,
      visible: currentItems.length,
      exe: countByFormat(currentItems, "exe"),
      msi: countByFormat(currentItems, "msi"),
      zip: countByFormat(currentItems, "zip"),
      filters: [tagFilter, colorTagFilter].filter(Boolean).length,
    }),
    [colorTagFilter, currentItems, softwareQuery.data?.total, tagFilter],
  );
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
    <section className="feature-shell software-workbench">
      <div className="feature-header software-workbench__header">
        <span className="page-header__eyebrow">{t("features.software.eyebrow")}</span>
        <h3>{t("features.software.title")}</h3>
        <p>{t("features.software.description")}</p>
      </div>

      <div className="software-summary-strip" aria-label={t("features.software.summary.ariaLabel")}>
        <div className="software-summary-strip__item">
          <span>{t("features.software.summary.total")}</span>
          <strong>{summaryStats.total.toLocaleString()}</strong>
        </div>
        <div className="software-summary-strip__item">
          <span>{t("features.software.summary.visible")}</span>
          <strong>{summaryStats.visible.toLocaleString()}</strong>
        </div>
        <div className="software-summary-strip__item">
          <span>{t("features.software.summary.exe")}</span>
          <strong>{summaryStats.exe.toLocaleString()}</strong>
        </div>
        <div className="software-summary-strip__item">
          <span>{t("features.software.summary.msi")}</span>
          <strong>{summaryStats.msi.toLocaleString()}</strong>
        </div>
        <div className="software-summary-strip__item">
          <span>{t("features.software.summary.zip")}</span>
          <strong>{summaryStats.zip.toLocaleString()}</strong>
        </div>
        <div className="software-summary-strip__item">
          <span>{t("features.software.summary.filters")}</span>
          <strong>{summaryStats.filters.toLocaleString()}</strong>
        </div>
      </div>

      <div className="software-action-bar">
        <div className="software-action-bar__copy">
          <span className="page-header__eyebrow">{t("features.software.quickActions.eyebrow")}</span>
          <p>{t("features.software.quickActions.description")}</p>
        </div>
        <div className="software-action-bar__actions">
          {!isBatchMode ? (
            <button className="ghost-button" type="button" onClick={enterBatchMode}>
              {t("common.actions.batchOrganize")}
            </button>
          ) : null}
          <button className="ghost-button" type="button" onClick={() => navigate("/search")}>
            {t("features.software.quickActions.search")}
          </button>
          <button className="ghost-button" type="button" onClick={() => navigate("/settings")}>
            {t("features.software.quickActions.sources")}
          </button>
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

      <div className="subset-filter-block software-filter-block">
        <div className="files-toolbar software-filter-toolbar">
          <label className="field-stack files-toolbar__field software-filter-toolbar__field">
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
          <label className="field-stack files-toolbar__field software-filter-toolbar__field">
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
          <label className="field-stack files-toolbar__field software-filter-toolbar__field">
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
          <label className="field-stack files-toolbar__field software-filter-toolbar__field">
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
        <div className="software-table software-table--loading" aria-label={t("features.software.loadingAria")}>
          {Array.from({ length: 8 }, (_, index) => (
            <SoftwareRowSkeleton key={index} />
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
          <div className="software-table" role="table" aria-label={t("features.software.table.ariaLabel")}>
            <div className="software-table__header" role="row">
              <span>{t("features.software.table.name")}</span>
              <span>{t("features.software.table.type")}</span>
              <span>{t("features.software.table.kind")}</span>
              <span>{t("features.software.table.modified")}</span>
              <span>{t("features.software.table.size")}</span>
              <span>{t("features.software.table.signals")}</span>
            </div>
            {softwareQuery.data.items.map((item) => (
              <SoftwareLibraryRow
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
