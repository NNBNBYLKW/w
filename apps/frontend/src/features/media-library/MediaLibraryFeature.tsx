import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
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
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}


const VIEW_SCOPE_OPTIONS: Array<{ label: string; value: MediaViewScope }> = [
  { label: "All media", value: "all" },
  { label: "Images", value: "image" },
  { label: "Videos", value: "video" },
];
const COLOR_TAG_OPTIONS: Array<{ label: string; value: ColorTagValue | "all" }> = [
  { label: "All colors", value: "all" },
  { label: "Red", value: "red" },
  { label: "Yellow", value: "yellow" },
  { label: "Green", value: "green" },
  { label: "Blue", value: "blue" },
  { label: "Purple", value: "purple" },
];

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
  const [thumbnailLoaded, setThumbnailLoaded] = useState(fileType !== "image");

  if (fileType !== "image" || thumbnailFailed) {
    return (
      <div className={`media-card__poster ${fileType === "video" ? "media-card__poster--video" : ""}`}>
        <div className="media-card__poster-copy">
          <strong>{fileType === "image" ? "Image preview unavailable" : "Video"}</strong>
          <span>{fileType === "image" ? "This indexed image has no preview yet." : "Visual browsing stays available."}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="media-card__poster media-card__poster--image">
      {!thumbnailLoaded ? <div className="media-card__poster-skeleton" aria-hidden="true" /> : null}
      <img
        className={`media-card__thumbnail${thumbnailLoaded ? " media-card__thumbnail--ready" : ""}`}
        src={getFileThumbnailUrl(fileId)}
        alt={`Thumbnail for ${name}`}
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
  modifiedAt,
  name,
  path,
  selected,
  sizeBytes,
  onSelect,
}: {
  fileId: number;
  fileType: "image" | "video";
  modifiedAt: string;
  name: string;
  path: string;
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
      </div>
    </button>
  );
}


export function MediaLibraryFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
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
      : tagsQuery.data?.items.find((tag) => String(tag.id) === selectedTagId)?.name ?? "Selected tag";
  const hasActiveFilters =
    viewScope !== "all" ||
    selectedTagId !== "all" ||
    selectedColorTag !== "all" ||
    sortBy !== "modified_at" ||
    sortOrder !== "desc";
  const filterSummary = hasActiveFilters
    ? [
        `Scope: ${VIEW_SCOPE_OPTIONS.find((option) => option.value === viewScope)?.label ?? "All media"}`,
        selectedTagName ? `Tag: ${selectedTagName}` : null,
        selectedColorTag !== "all"
          ? `Color: ${COLOR_TAG_OPTIONS.find((option) => option.value === selectedColorTag)?.label ?? selectedColorTag}`
          : null,
        `Sorted by ${sortBy === "modified_at" ? "Modified" : sortBy === "name" ? "Name" : "Discovered"} (${sortOrder === "desc" ? "Descending" : "Ascending"})`,
      ]
        .filter(Boolean)
        .join(" · ")
    : "Showing all indexed images and videos.";

  const resetFilters = () => {
    setViewScope("all");
    setSelectedTagId("all");
    setSelectedColorTag("all");
    setSortBy("modified_at");
    setSortOrder("desc");
    setPage(1);
  };

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Visual subset browsing</span>
        <h3>Image and video library</h3>
        <p>Select a card to load shared details. Double-click a card to open the indexed file in the desktop shell.</p>
      </div>

      <div className="media-library-toolbar">
        <div className="field-stack media-library-toolbar__field media-library-toolbar__field--wide">
          <span>Scope</span>
          <div className="media-library-scope-switch" aria-label="Media library scope">
            {VIEW_SCOPE_OPTIONS.map((option) => (
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
          <span>Tag</span>
          <select
            className="select-input"
            value={selectedTagId}
            onChange={(event) => {
              setSelectedTagId(event.target.value);
              setPage(1);
            }}
            disabled={tagsQuery.isLoading || tagsQuery.error instanceof Error}
          >
            <option value="all">{tagsQuery.error instanceof Error ? "Tags unavailable" : "All tags"}</option>
            {(tagsQuery.data?.items ?? []).map((tag) => (
              <option key={tag.id} value={tag.id}>
                {tag.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack media-library-toolbar__field">
          <span>Color</span>
          <select
            className="select-input"
            value={selectedColorTag}
            onChange={(event) => {
              setSelectedColorTag(event.target.value as ColorTagValue | "all");
              setPage(1);
            }}
          >
            {COLOR_TAG_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack media-library-toolbar__field">
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
        <label className="field-stack media-library-toolbar__field">
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
      </div>
      <div className="media-library-filter-summary">
        <p>{filterSummary}</p>
        {hasActiveFilters ? (
          <button className="ghost-button media-library-filter-summary__clear" type="button" onClick={resetFilters}>
            Clear filters
          </button>
        ) : null}
      </div>

      <div className="media-library-meta-row">
        <p>
          {viewScope === "all"
            ? "Showing active indexed images and videos in a visual-first media library view."
            : `Showing active indexed ${viewScope} files in the current media library scope.`}
        </p>
        {mediaQuery.data ? <span>{mediaQuery.data.total} media items</span> : null}
      </div>

      {showLoadingSkeleton ? (
        <div className="media-library-grid media-library-grid--loading" aria-label="Loading media library">
          {Array.from({ length: 8 }, (_, index) => (
            <MediaCardSkeleton key={index} />
          ))}
        </div>
      ) : null}

      {mediaQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Media library failed</strong>
          <p>{mediaQuery.error.message}</p>
        </div>
      ) : null}

      {tagsQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Tag filters unavailable</strong>
          <p>{tagsQuery.error.message}</p>
        </div>
      ) : null}

      {showEmptyState ? (
        <div className="future-frame">
          No active indexed image or video files are available yet. Add a source and run a scan to populate this
          media subset surface.
        </div>
      ) : null}

      {showNoResultsState ? (
        <div className="future-frame">
          No indexed media files match the current scope and filter set on this page. Adjust the filters or clear them
          to keep browsing.
        </div>
      ) : null}

      {mediaQuery.data && mediaQuery.data.items.length > 0 ? (
        <>
          <div className="media-library-grid">
            {mediaQuery.data.items.map((item) => (
              <MediaLibraryCard
                key={item.id}
                fileId={item.id}
                fileType={item.file_type}
                modifiedAt={item.modified_at}
                name={item.name}
                path={item.path}
                selected={selectedItemId === String(item.id)}
                sizeBytes={item.size_bytes}
                onSelect={() => selectItem(String(item.id))}
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
