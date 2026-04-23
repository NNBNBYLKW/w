import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
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
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}

function formatSoftwareFormat(value: SoftwareFormat): string {
  return value.toUpperCase();
}

function formatModifiedAt(value: string): string {
  return new Date(value).toLocaleString();
}

function buildSoftwareEntryLabel(value: SoftwareFormat): string {
  if (value === "exe") {
    return "Executable entry";
  }
  if (value === "msi") {
    return "Installer entry";
  }
  return "Archive entry";
}

function buildSoftwareFormatHint(value: SoftwareFormat): string {
  if (value === "exe") {
    return "Local application or utility file";
  }
  if (value === "msi") {
    return "Windows installer package";
  }
  return "Compressed distribution archive";
}

function buildSoftwareFormatCopy(value: SoftwareFormat): string {
  if (value === "exe") {
    return "EXE executable";
  }
  if (value === "msi") {
    return "MSI installer package";
  }
  return "ZIP archive package";
}

function formatColorTagLabel(value: ColorTagValue): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
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
          <span className="software-card__poster-eyebrow">Software entry</span>
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
        {isFavorite ? <span className="status-pill status-pill--favorite">★ Favorite</span> : null}
        {rating !== null ? <span className="status-pill status-pill--rating">★ {rating}</span> : null}
        {isBatchMode && selected ? <span className="status-pill">Selected</span> : null}
      </div>
      <span className="software-card__hint">
        Single-click for shared details. Double-click to open the software-related file.
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
    pageLabel: "Software",
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
    return parts.length > 0 ? `Showing: ${parts.join(" · ")}` : "Showing all recognized software-related files.";
  }, [colorTagFilter, selectedTagLabel, sortBy, sortOrder]);
  const entryCopy = useMemo(() => {
    if (entry === "recent") {
      return "Opened from Recent so you can continue organizing this software-related file inside the Software subset surface.";
    }
    if (entry === "tags") {
      return "Opened from Tags so you can review the software subset attached to the current tag.";
    }
    if (entry === "collections") {
      return "Opened from Collections so you can browse the software subset represented by the selected retrieval.";
    }
    if (entry === "details") {
      return "Opened from shared details so you can re-find this software-related file inside the Software subset surface.";
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
      defaultNameParts.length > 0 ? `${defaultNameParts.join(" ")} Software` : "Software Collection",
    );
    navigate(`/collections?${params.toString()}`);
  };

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Library subset browsing</span>
        <h3>Recognized software-related files</h3>
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

      <div className="software-filter-summary">
        <p>
          {hasActiveSoftwareFilters
            ? filterSummary
            : `Showing all recognized software-related files. Sorted by ${sortBy === "modified_at" ? "Modified" : sortBy === "name" ? "Name" : "Discovered"} (${sortOrder === "desc" ? "Descending" : "Ascending"}).`}
        </p>
        <div className="software-filter-summary__actions">
          {!isBatchMode ? (
            <button className="ghost-button" type="button" onClick={enterBatchMode}>
              Batch organize
            </button>
          ) : null}
          {hasActiveSoftwareFilters ? (
            <>
              <button className="ghost-button" type="button" onClick={clearSoftwareFilters}>
                Clear filters
              </button>
              <button className="ghost-button" type="button" onClick={saveCurrentSoftwareFiltersAsCollection}>
                Save current software filters as collection
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
        <p>
          Showing recognized .exe, .msi, and .zip files from the active indexed library with software-first entry
          cues, type labels, and the shared workbench actions.
        </p>
        {softwareQuery.data ? <span>{softwareQuery.data.total} software-related files</span> : null}
      </div>

      {showLoadingSkeleton ? (
        <div className="software-library-grid software-library-grid--loading" aria-label="Loading software library">
          {Array.from({ length: 8 }, (_, index) => (
            <SoftwareCardSkeleton key={index} />
          ))}
        </div>
      ) : null}

      {softwareQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Software listing failed</strong>
          <p>{softwareQuery.error.message}</p>
        </div>
      ) : null}

      {showEmptyState ? (
        <div className="future-frame">
          No recognized software-related files are available yet. Add a source and run a scan to populate this subset
          surface.
        </div>
      ) : null}

      {showNoResultsState ? (
        <div className="future-frame">
          No recognized software-related files match the current page and filters. Move between pages or change sorting
          to keep browsing.
        </div>
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
