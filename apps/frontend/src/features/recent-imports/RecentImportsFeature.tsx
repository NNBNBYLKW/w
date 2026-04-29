import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
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
  return value === null ? t("common.states.unavailable") : `${value.toLocaleString()} bytes`;
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
      label: t("features.recent.openInMedia"),
      to: `/library/media?${params.toString()}`,
    };
  }

  if (inferBookFile(item.name, item.path)) {
    const params = new URLSearchParams({
      focus: String(item.id),
      entry: "recent",
    });
    return {
      label: t("features.recent.openInBooks"),
      to: `/library/books?${params.toString()}`,
    };
  }

  if (inferGameFile(item.name, item.path)) {
    const params = new URLSearchParams({
      focus: String(item.id),
      entry: "recent",
    });
    return {
      label: t("features.recent.openInGames"),
      to: `/library/games?${params.toString()}`,
    };
  }

  if (inferSoftwareFile(item.name, item.path)) {
    const params = new URLSearchParams({
      focus: String(item.id),
      entry: "recent",
    });
    return {
      label: t("features.recent.openInSoftware"),
      to: `/software?${params.toString()}`,
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


export function RecentImportsFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const navigate = useNavigate();
  const familyOptions: Array<{ label: string; value: RecentFamilyKind }> = [
    { label: t("features.recent.families.imports"), value: "imports" },
    { label: t("features.recent.families.tagged"), value: "tagged" },
    { label: t("features.recent.families.colorTagged"), value: "color-tagged" },
  ];
  const rangeOptions: Array<{ label: string; hint: string; value: RecentRangeValue }> = [
    { label: t("features.recent.ranges.oneDay"), hint: t("features.recent.ranges.oneDayHint"), value: "1d" },
    { label: t("features.recent.ranges.sevenDays"), hint: t("features.recent.ranges.sevenDaysHint"), value: "7d" },
    { label: t("features.recent.ranges.thirtyDays"), hint: t("features.recent.ranges.thirtyDaysHint"), value: "30d" },
  ];
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
    pageLabel: t("shell.topbar.pages.recent"),
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

  const selectedRangeLabel = rangeOptions.find((option) => option.value === range)?.hint ?? t("features.recent.ranges.sevenDaysHint");
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
      ? t("features.recent.descriptions.imports", { range: selectedRangeLabel })
      : family === "tagged"
        ? t("features.recent.descriptions.tagged", { range: selectedRangeLabel })
        : t("features.recent.descriptions.colorTagged", { range: selectedRangeLabel });

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">{t("features.recent.eyebrow")}</span>
        <h3>{t("features.recent.title")}</h3>
        <p>{t("features.recent.description")}</p>
      </div>

      <div className="recent-toolbar">
        <div className="recent-range-switch" aria-label={t("pages.recent.title")}>
          {familyOptions.map((option) => (
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
        <div className="recent-range-switch" aria-label={t("pages.recent.eyebrow")}>
          {rangeOptions.map((option) => (
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
          <span>{t("common.labels.order")}</span>
          <select
            className="select-input"
            value={sortOrder}
            onChange={(event) => {
              setSortOrder(event.target.value as FileListSortOrder);
              setPage(1);
            }}
          >
            <option value="desc">{t("common.sortOrder.newestFirst")}</option>
            <option value="asc">{t("common.sortOrder.oldestFirst")}</option>
          </select>
        </label>
      </div>

      <div className="recent-meta-row">
        <p>{familyDescription}</p>
        <div className="files-meta-row__actions">
          {activeQuery.data ? <span>{t("common.labels.files", { count: activeQuery.data.total })}</span> : null}
          {family === "imports" && !isBatchMode ? (
            <button className="ghost-button" type="button" onClick={enterBatchMode}>
              {t("common.actions.batchOrganize")}
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

      {activeQuery.isLoading ? <p>{t("features.recent.loading")}</p> : null}

      {activeQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.recent.failedTitle")}</strong>
          <p>{activeQuery.error.message}</p>
        </div>
      ) : null}

      {activeQuery.data && items.length === 0 ? (
        <div className="future-frame">
          {family === "imports"
            ? t("features.recent.emptyImports")
            : family === "tagged"
              ? t("features.recent.emptyTagged")
              : t("features.recent.emptyColorTagged")}
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
                      {isImportsBatch && isSelected(item.id) ? <span className="status-pill">{t("common.states.selected")}</span> : null}
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
