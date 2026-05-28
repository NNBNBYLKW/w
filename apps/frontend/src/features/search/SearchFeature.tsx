import { FormEvent, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
import { EmptyState, Pagination, WorkbenchFilterPanel, WorkbenchMasthead, WorkbenchPage, WorkbenchResultFrame, WorkbenchToolbar } from "../../shared/ui/components";
import { AssetIconGrid, ViewModeToggle, useViewMode, type AssetIconCardItem } from "../../shared/ui/view-mode";
import { useThumbnailWarmup } from "../../shared/ui/thumbnail";
import type {
  ColorTagValue,
  FileType,
  LibraryPlacementFilter,
  SearchSortBy,
  SearchSortOrder,
  StorageStateFilter,
} from "../../entities/file/types";
import { getFileThumbnailUrl } from "../../services/api/fileDetailsApi";
import { searchFiles } from "../../services/api/searchApi";
import { listTags } from "../../services/api/tagsApi";
import {
  hasDesktopOpenActionsBridge,
  normalizeIndexedFilePath,
  openIndexedFile,
} from "../../services/desktop/openActions";
import { queryKeys } from "../../services/query/queryKeys";
import { setWorkbenchFileDragData } from "../../services/tools/videoMergeDrag";


function formatSearchModifiedAt(value: string): string {
  return new Date(value).toLocaleString();
}

function getSearchTypeMark(fileType: FileType): string {
  if (fileType === "image") {
    return "IMG";
  }
  if (fileType === "video") {
    return "VID";
  }
  if (fileType === "document") {
    return "DOC";
  }
  if (fileType === "archive") {
    return "ZIP";
  }
  return "FILE";
}

function getSearchTypeLabel(fileType: FileType): string {
  if (fileType === "image") {
    return t("common.fileTypes.image");
  }
  if (fileType === "video") {
    return t("common.fileTypes.video");
  }
  if (fileType === "document") {
    return t("common.fileTypes.document");
  }
  if (fileType === "archive") {
    return t("common.fileTypes.archive");
  }
  return t("common.fileTypes.other");
}


const RECENT_KEY = "workbench_recent_searches";
function useSearchHistory() {
  const [recent, setRecent] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]"); } catch { return []; }
  });
  const addSearch = (q: string) => {
    if (!q.trim()) return;
    const next = [q, ...recent.filter(s => s !== q)].slice(0, 10);
    setRecent(next);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  };
  return { recent, addSearch };
}

export function SearchFeature() {
  const { recent, addSearch } = useSearchHistory();
  const [showHistory, setShowHistory] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const navigate = useNavigate();
  const { viewMode, setViewMode } = useViewMode("search");
  const fileTypeOptions: Array<{ label: string; value: FileType | "all" }> = [
    { label: t("common.fileTypes.all"), value: "all" },
    { label: t("common.fileTypes.image"), value: "image" },
    { label: t("common.fileTypes.video"), value: "video" },
    { label: t("common.fileTypes.document"), value: "document" },
    { label: t("common.fileTypes.archive"), value: "archive" },
    { label: t("common.fileTypes.other"), value: "other" },
  ];
  const libraryPlacementOptions: Array<{ label: string; value: LibraryPlacementFilter | "all" }> = [
    { label: t("common.libraryPlacements.all"), value: "all" },
    { label: t("common.libraryPlacements.documents"), value: "documents" },
    { label: t("common.libraryPlacements.media"), value: "media" },
    { label: t("common.libraryPlacements.games"), value: "games" },
    { label: t("common.libraryPlacements.software"), value: "software" },
  ];
  const storageStateOptions: Array<{ label: string; value: StorageStateFilter | "all" }> = [
    { label: t("common.storageScope.all"), value: "all" },
    { label: t("common.storageScope.external"), value: "external" },
    { label: t("common.storageScope.inbox"), value: "inbox" },
    { label: t("common.storageScope.managed"), value: "managed" },
  ];
  const colorTagOptions: Array<{ label: string; value: ColorTagValue | "all" }> = [
    { label: t("common.colors.all"), value: "all" },
    { label: t("common.colors.red"), value: "red" },
    { label: t("common.colors.yellow"), value: "yellow" },
    { label: t("common.colors.green"), value: "green" },
    { label: t("common.colors.blue"), value: "blue" },
    { label: t("common.colors.purple"), value: "purple" },
  ];
  const [inputQuery, setInputQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [fileType, setFileType] = useState<FileType | "all">("all");
  const [libraryPlacement, setLibraryPlacement] = useState<LibraryPlacementFilter | "all">("all");
  const [storageState, setStorageState] = useState<StorageStateFilter | "all">("all");
  const [selectedTagId, setSelectedTagId] = useState("all");
  const [selectedColorTag, setSelectedColorTag] = useState<ColorTagValue | "all">("all");
  const [isFavorite, setIsFavorite] = useState<boolean>(false);
  const [minRating, setMinRating] = useState<number>(0);
  const [sortBy, setSortBy] = useState<SearchSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<SearchSortOrder>("desc");
  const [page, setPage] = useState(1);
  const tagsQuery = useQuery({
    queryKey: queryKeys.tags,
    queryFn: listTags,
  });

  const queryParams = {
    query: appliedQuery,
    file_type: fileType === "all" ? undefined : fileType,
    library_placement: libraryPlacement === "all" ? undefined : libraryPlacement,
    storage_state: storageState === "all" ? undefined : storageState,
    tag_id: selectedTagId === "all" ? undefined : Number(selectedTagId),
    color_tag: selectedColorTag === "all" ? undefined : selectedColorTag,
    is_favorite: isFavorite || undefined,
    min_rating: minRating > 0 ? minRating : undefined,
    page,
    page_size: 50,
    sort_by: sortBy,
    sort_order: sortOrder,
  } as const;

  const searchQuery = useQuery({
    queryKey: queryKeys.search(queryParams),
    queryFn: () => searchFiles(queryParams),
  });

  const totalPages = searchQuery.data ? Math.max(1, Math.ceil(searchQuery.data.total / searchQuery.data.page_size)) : 1;
  const iconItems = (searchQuery.data?.items ?? []).map(
    (item): AssetIconCardItem => ({
      id: item.id,
      title: item.name,
      path: item.path,
      typeLabel: getSearchTypeLabel(item.file_type),
      meta: formatSearchModifiedAt(item.modified_at),
      mark: getSearchTypeMark(item.file_type),
      markTone: item.file_type,
      thumbnailUrl:
        item.file_type === "image" || item.file_type === "video" || item.file_type === "document"
          ? getFileThumbnailUrl(item.id)
          : undefined,
      thumbnailAlt: item.name,
      selected: selectedItemId === String(item.id),
    }),
  );
  const thumbnailWarmup = useThumbnailWarmup(iconItems.filter((item) => item.thumbnailUrl).map((item) => item.id));

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const q = inputQuery.trim();
    if (!q) return;
    addSearch(q);
    setAppliedQuery(q);
    setPage(1);
    setShowHistory(false);
  };

  const resultMeta = (
    <>
      <p>
        {appliedQuery ? t("features.search.matches", { query: appliedQuery }) : t("features.search.emptyQuery")}
      </p>
      {searchQuery.data ? <span>{t("common.labels.results", { count: searchQuery.data.total })}</span> : null}
    </>
  );

  return (
    <WorkbenchPage className="browse-surface browse-surface--search" variant="search">
      <WorkbenchMasthead
        eyebrow={t("features.search.eyebrow")}
        title={t("features.search.title")}
        description={t("pages.search.description")}
      />

      <form className="search-workbench-form" onSubmit={handleSubmit}>
        <div className="search-command-row">
          <div style={{ position: "relative", flex: 1 }}>
            <input
              ref={inputRef}
              className="text-input search-command-row__input"
              type="search"
              name="search"
              autoComplete="off"
              value={inputQuery}
              onChange={(event) => setInputQuery(event.target.value)}
              onFocus={() => setShowHistory(true)}
              onBlur={() => setTimeout(() => setShowHistory(false), 200)}
              placeholder={t("features.search.placeholder")}
              aria-label={t("features.search.placeholder")}
            />
            {showHistory && !inputQuery.trim() && recent.length > 0 ? (
              <div
                style={{
                  position: "absolute", top: "100%", left: 0, right: 0,
                  background: "var(--color-surface, #fff)", border: "1px solid var(--color-border, #ddd)",
                  borderRadius: 8, zIndex: 100, boxShadow: "0 4px 12px rgba(0,0,0,0.1)", marginTop: 4,
                }}
              >
                {recent.map((q) => (
                  <button
                    key={q}
                    type="button"
                    style={{
                      display: "block", width: "100%", textAlign: "left", padding: "8px 12px",
                      border: "none", background: "none", cursor: "pointer", fontSize: 14,
                    }}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      setInputQuery(q);
                      addSearch(q);
                      setAppliedQuery(q);
                      setPage(1);
                      setShowHistory(false);
                    }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--color-hover, #f5f5f5)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = ""; }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <button className="primary-button" type="submit">
            {t("common.actions.search")}
          </button>
        </div>

        <WorkbenchFilterPanel className="search-filter-panel" label={t("features.search.title")}>
          <WorkbenchToolbar className="search-toolbar">
          <label className="field-stack search-toolbar__field">
            <span>{t("common.labels.type")}</span>
            <select
              className="select-input"
              value={fileType}
              onChange={(event) => {
                setFileType(event.target.value as FileType | "all");
                setPage(1);
              }}
            >
              {fileTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack search-toolbar__field">
            <span>{t("common.labels.library")}</span>
            <select
              className="select-input"
              value={libraryPlacement}
              onChange={(event) => {
                setLibraryPlacement(event.target.value as LibraryPlacementFilter | "all");
                setPage(1);
              }}
            >
              {libraryPlacementOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack search-toolbar__field">
            <span>{t("common.labels.storageScope")}</span>
            <select
              className="select-input"
              value={storageState}
              onChange={(event) => {
                setStorageState(event.target.value as StorageStateFilter | "all");
                setPage(1);
              }}
            >
              {storageStateOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack search-toolbar__field">
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
          <label className="field-stack search-toolbar__field">
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
          <label className="field-stack search-toolbar__field search-toolbar__field--checkbox">
            <span>Favorites only</span>
            <input
              type="checkbox"
              className="checkbox-input"
              checked={isFavorite}
              onChange={(event) => {
                setIsFavorite(event.target.checked);
                setPage(1);
              }}
            />
          </label>
          <label className="field-stack search-toolbar__field">
            <span>Min rating</span>
            <select
              className="select-input"
              value={minRating}
              onChange={(event) => {
                setMinRating(Number(event.target.value));
                setPage(1);
              }}
            >
              <option value={0}>Any</option>
              <option value={1}>1 star</option>
              <option value={2}>2 stars</option>
              <option value={3}>3 stars</option>
              <option value={4}>4 stars</option>
              <option value={5}>5 stars</option>
            </select>
          </label>
          <label className="field-stack search-toolbar__field">
            <span>{t("common.labels.sortBy")}</span>
            <select
              className="select-input"
              value={sortBy}
              onChange={(event) => {
                setSortBy(event.target.value as SearchSortBy);
                setPage(1);
              }}
            >
              <option value="modified_at">{t("common.sortBy.modified")}</option>
              <option value="name">{t("common.sortBy.name")}</option>
              <option value="discovered_at">{t("common.sortBy.discovered")}</option>
            </select>
          </label>
          <label className="field-stack search-toolbar__field">
            <span>{t("common.labels.order")}</span>
            <select
              className="select-input"
              value={sortOrder}
              onChange={(event) => {
                setSortOrder(event.target.value as SearchSortOrder);
                setPage(1);
              }}
            >
              <option value="desc">{t("common.sortOrder.descending")}</option>
              <option value="asc">{t("common.sortOrder.ascending")}</option>
            </select>
          </label>
          <div className="compact-filter-toolbar__view-mode">
            <ViewModeToggle value={viewMode} onChange={setViewMode} />
          </div>
          </WorkbenchToolbar>
        </WorkbenchFilterPanel>
      </form>

      <WorkbenchResultFrame className="search-result-frame" title={t("features.search.title")} meta={resultMeta}>
        {searchQuery.isLoading ? (
          <p role="status" aria-live="polite">
            {t("features.search.loading")}
          </p>
        ) : null}

        {searchQuery.error instanceof Error ? (
          <div className="status-block page-card">
            <strong>{t("features.search.failedTitle")}</strong>
            <p>{searchQuery.error.message}</p>
          </div>
        ) : null}

        {tagsQuery.error instanceof Error ? (
          <div className="status-block page-card">
            <strong>{t("features.search.tagsUnavailableTitle")}</strong>
            <p>{tagsQuery.error.message}</p>
          </div>
        ) : null}

        {searchQuery.data && searchQuery.data.items.length === 0 ? (
          <EmptyState title={t("features.search.empty")} description={t("features.search.emptyGuide")}
            action={{ label: t("features.homeOverview.scanCardAction"), onClick: () => navigate("/library?tab=sources") }} />
        ) : null}

        {searchQuery.data && searchQuery.data.items.length > 0 ? (
          <>
          {viewMode === "icons" ? (
            <AssetIconGrid
              ariaLabel={t("features.search.title")}
              items={iconItems}
              getThumbnailRefreshToken={(item) => thumbnailWarmup.getRefreshToken(item.id)}
              isThumbnailDisabled={(item) => thumbnailWarmup.isThumbnailDisabled(item.id)}
              onThumbnailLoaded={(item) => thumbnailWarmup.markLoaded(item.id)}
              onSelect={(item) => selectItem(String(item.id))}
              onOpen={(iconItem) => {
                const matchedItem = searchQuery.data.items.find((item) => item.id === iconItem.id);
                const normalizedPath = normalizeIndexedFilePath(matchedItem?.path);
                if (!normalizedPath || !hasDesktopOpenActionsBridge()) {
                  return;
                }
                void openIndexedFile(normalizedPath);
              }}
            />
          ) : (
            <div className="search-results">
              {searchQuery.data.items.map((item) => (
                <button
                  key={item.id}
                  className={`search-result-row${selectedItemId === String(item.id) ? " search-result-row--selected" : ""}`}
                  type="button"
                  draggable={item.file_type === "video"}
                  onDragStart={(event) => {
                    if (item.file_type !== "video") {
                      return;
                    }
                    setWorkbenchFileDragData(event, {
                      file_id: item.id,
                      name: item.name,
                      path: item.path,
                      file_type: item.file_type,
                    });
                  }}
                  onClick={() => selectItem(String(item.id))}
                  onDoubleClick={() => {
                    const normalizedPath = normalizeIndexedFilePath(item.path);
                    if (!normalizedPath || !hasDesktopOpenActionsBridge()) {
                      return;
                    }
                    void openIndexedFile(normalizedPath);
                  }}
                >
                  <div className="search-result-row__meta">
                    <strong>{item.name}</strong>
                    <p>{item.path}</p>
                  </div>
                  <div className="search-result-row__badges">
                    <span className="status-pill">{item.file_type}</span>
                    <span className="status-pill">{formatSearchModifiedAt(item.modified_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </>
        ) : null}
      </WorkbenchResultFrame>
    </WorkbenchPage>
  );
}
