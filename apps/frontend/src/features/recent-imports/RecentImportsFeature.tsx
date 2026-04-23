import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import type { FileListSortOrder } from "../../entities/file/types";
import type { RecentActivityListItemVM, RecentFamilyKind, RecentRangeValue } from "../../entities/recent/types";
import { BatchActionBar } from "../batch-organize/BatchActionBar";
import { useBatchOrganizeActions } from "../batch-organize/useBatchOrganizeActions";
import { useBatchSelection } from "../batch-organize/useBatchSelection";
import {
  hasDesktopOpenActionsBridge,
  normalizeIndexedFilePath,
  openIndexedFile,
} from "../../services/desktop/openActions";
import { listRecentColorTagged, listRecentImports, listRecentTagged } from "../../services/api/recentApi";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}

function inferBookFile(name: string, path: string): boolean {
  const candidate = `${name} ${path}`.toLowerCase();
  return candidate.includes(".epub") || candidate.includes(".pdf");
}

function inferSoftwareFile(name: string, path: string): boolean {
  const candidate = `${name} ${path}`.toLowerCase();
  return candidate.includes(".exe") || candidate.includes(".msi") || candidate.includes(".zip");
}

function inferGameFile(name: string, path: string): boolean {
  const candidate = `${name} ${path}`.toLowerCase();
  if (candidate.includes(".lnk")) {
    return true;
  }
  if (!candidate.includes(".exe")) {
    return false;
  }

  return [
    "\\games\\",
    "\\game\\",
    "\\steam\\",
    "\\steamapps\\",
    "\\gog\\",
    "\\epic games\\",
    "\\itch\\",
    "\\riot games\\",
    "\\blizzard\\",
    "\\battle.net\\",
    "\\ubisoft\\",
    "\\rockstar games\\",
    "\\ea games\\",
  ].some((hint) => candidate.includes(hint));
}

function getSubsetTarget(item: RecentActivityListItemVM): { label: string; to: string } | null {
  if (item.file_type === "image" || item.file_type === "video") {
    const params = new URLSearchParams({
      view_scope: item.file_type,
      focus: String(item.id),
      entry: "recent",
    });
    return {
      label: "Open in Media",
      to: `/library/media?${params.toString()}`,
    };
  }

  if (inferBookFile(item.name, item.path)) {
    const params = new URLSearchParams({
      focus: String(item.id),
      entry: "recent",
    });
    return {
      label: "Open in Books",
      to: `/library/books?${params.toString()}`,
    };
  }

  if (inferGameFile(item.name, item.path)) {
    const params = new URLSearchParams({
      focus: String(item.id),
      entry: "recent",
    });
    return {
      label: "Open in Games",
      to: `/library/games?${params.toString()}`,
    };
  }

  if (inferSoftwareFile(item.name, item.path)) {
    const params = new URLSearchParams({
      focus: String(item.id),
      entry: "recent",
    });
    return {
      label: "Open in Software",
      to: `/library/software?${params.toString()}`,
    };
  }

  return null;
}

async function openRecentFile(path: string) {
  if (!hasDesktopOpenActionsBridge()) {
    return;
  }

  const normalizedPath = normalizeIndexedFilePath(path);
  if (!normalizedPath) {
    return;
  }

  await openIndexedFile(normalizedPath);
}


const FAMILY_OPTIONS: Array<{ label: string; value: RecentFamilyKind }> = [
  { label: "Imports", value: "imports" },
  { label: "Tagged", value: "tagged" },
  { label: "Color-tagged", value: "color-tagged" },
];

const RANGE_OPTIONS: Array<{ label: string; hint: string; value: RecentRangeValue }> = [
  { label: "1 day", hint: "Last 1 day", value: "1d" },
  { label: "7 days", hint: "Last 7 days", value: "7d" },
  { label: "30 days", hint: "Last 30 days", value: "30d" },
];


export function RecentImportsFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const navigate = useNavigate();
  const [family, setFamily] = useState<RecentFamilyKind>("imports");
  const [range, setRange] = useState<RecentRangeValue>("7d");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");
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
    pageLabel: "Recent Imports",
    resetDeps: [family, range, sortOrder, page],
  });
  const { applyColorTag, applyTag, isApplyingColorTag, isApplyingTag } = useBatchOrganizeActions({
    onSuccess: clearSelection,
  });

  useEffect(() => {
    if (family !== "imports" && isBatchMode) {
      exitBatchMode();
    }
  }, [exitBatchMode, family, isBatchMode]);

  const selectedRangeLabel = RANGE_OPTIONS.find((option) => option.value === range)?.hint ?? "Last 7 days";
  const queryParams = {
    range,
    page,
    page_size: 50,
    sort_order: sortOrder,
  } as const;

  const recentImportsQuery = useQuery({
    queryKey: queryKeys.recent(queryParams),
    queryFn: () => listRecentImports(queryParams),
    enabled: family === "imports",
  });
  const recentTaggedQuery = useQuery({
    queryKey: queryKeys.recentTagged(queryParams),
    queryFn: () => listRecentTagged(queryParams),
    enabled: family === "tagged",
  });
  const recentColorTaggedQuery = useQuery({
    queryKey: queryKeys.recentColorTagged(queryParams),
    queryFn: () => listRecentColorTagged(queryParams),
    enabled: family === "color-tagged",
  });

  const activeQuery = family === "imports" ? recentImportsQuery : family === "tagged" ? recentTaggedQuery : recentColorTaggedQuery;
  const items = useMemo<RecentActivityListItemVM[]>(() => {
    if (family === "imports") {
      return recentImportsQuery.data?.items.map((item) => ({
        ...item,
        occurred_at: item.discovered_at,
      })) ?? [];
    }
    return activeQuery.data?.items ?? [];
  }, [activeQuery.data?.items, family, recentImportsQuery.data?.items]);

  const totalPages = activeQuery.data ? Math.max(1, Math.ceil(activeQuery.data.total / activeQuery.data.page_size)) : 1;
  const familyDescription =
    family === "imports"
      ? `Showing active indexed files first discovered in the selected recent window: ${selectedRangeLabel}.`
      : family === "tagged"
        ? `Showing active indexed files most recently tagged in the selected recent window: ${selectedRangeLabel}.`
        : `Showing active indexed files whose current color tag was most recently updated in the selected recent window: ${selectedRangeLabel}.`;

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Recent family</span>
        <h3>Recent retrieval surfaces</h3>
        <p>Use Recent Imports, Tagged, and Color-tagged as lightweight retrieval surfaces. Single-click still loads shared details and double-click still opens the indexed file.</p>
      </div>

      <div className="recent-toolbar">
        <div className="recent-range-switch" aria-label="Recent family">
          {FAMILY_OPTIONS.map((option) => (
            <button
              key={option.value}
              className={`secondary-button recent-range-button${family === option.value ? " recent-range-button--selected" : ""}`}
              type="button"
              onClick={() => {
                setFamily(option.value);
                setPage(1);
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
        <div className="recent-range-switch" aria-label="Recent range">
          {RANGE_OPTIONS.map((option) => (
            <button
              key={option.value}
              className={`secondary-button recent-range-button${range === option.value ? " recent-range-button--selected" : ""}`}
              type="button"
              onClick={() => {
                setRange(option.value);
                setPage(1);
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
        <label className="field-stack recent-toolbar__field">
          <span>Order</span>
          <select
            className="select-input"
            value={sortOrder}
            onChange={(event) => {
              setSortOrder(event.target.value as FileListSortOrder);
              setPage(1);
            }}
          >
            <option value="desc">Newest first</option>
            <option value="asc">Oldest first</option>
          </select>
        </label>
      </div>

      <div className="recent-meta-row">
        <p>{familyDescription}</p>
        <div className="files-meta-row__actions">
          {activeQuery.data ? <span>{activeQuery.data.total} files</span> : null}
          {family === "imports" && !isBatchMode ? (
            <button className="ghost-button" type="button" onClick={enterBatchMode}>
              Batch organize
            </button>
          ) : null}
        </div>
      </div>

      {family === "imports" && isBatchMode ? (
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

      {activeQuery.isLoading ? <p>Loading recent retrieval...</p> : null}

      {activeQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Recent family failed</strong>
          <p>{activeQuery.error.message}</p>
        </div>
      ) : null}

      {activeQuery.data && items.length === 0 ? (
        <div className="future-frame">
          {family === "imports"
            ? "No active indexed files were discovered in this recent window yet."
            : family === "tagged"
              ? "No active indexed files were tagged in this recent window yet."
              : "No active indexed files currently carry a color tag updated in this recent window."}
        </div>
      ) : null}

      {activeQuery.data && items.length > 0 ? (
        <>
          <div className="recent-list">
            {items.map((item) => {
              const subsetTarget = getSubsetTarget(item);
              const isImportsBatch = family === "imports" && isBatchMode;

              return (
                <div key={`${family}-${item.id}`} className="recent-row-shell">
                  <button
                    className={`recent-row${
                      isImportsBatch
                        ? isSelected(item.id)
                          ? " recent-row--selected"
                          : ""
                        : selectedItemId === String(item.id)
                          ? " recent-row--selected"
                          : ""
                    }`}
                    type="button"
                    onClick={() => {
                      if (isImportsBatch) {
                        toggleSelection(item.id);
                        return;
                      }
                      selectItem(String(item.id));
                    }}
                    onDoubleClick={() => {
                      if (isImportsBatch) {
                        return;
                      }
                      void openRecentFile(item.path);
                    }}
                    >
                      <div className="recent-row__meta">
                        <strong title={item.name}>{item.name}</strong>
                        <p title={item.path}>{item.path}</p>
                      </div>
                    <div className="recent-row__badges">
                      <span className="status-pill">{item.file_type}</span>
                      <span className="status-pill">{new Date(item.occurred_at).toLocaleString()}</span>
                      <span className="status-pill">{formatBytes(item.size_bytes)}</span>
                      {isImportsBatch && isSelected(item.id) ? <span className="status-pill">Selected</span> : null}
                    </div>
                  </button>
                  {!isImportsBatch && subsetTarget ? (
                    <button
                      className="secondary-button recent-row-shell__action"
                      type="button"
                      onClick={() => {
                        navigate(subsetTarget.to);
                      }}
                    >
                      {subsetTarget.label}
                    </button>
                  ) : null}
                </div>
              );
            })}
          </div>
          <div className="recent-pager">
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
