import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import type { FileListSortBy, FileListSortOrder } from "../../entities/file/types";
import type { MediaViewScope } from "../../entities/media/types";
import { listMediaLibrary } from "../../services/api/mediaLibraryApi";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}


const VIEW_SCOPE_OPTIONS: Array<{ label: string; value: MediaViewScope }> = [
  { label: "All media", value: "all" },
  { label: "Images", value: "image" },
  { label: "Videos", value: "video" },
];


export function MediaLibraryFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const [viewScope, setViewScope] = useState<MediaViewScope>("all");
  const [sortBy, setSortBy] = useState<FileListSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");
  const [page, setPage] = useState(1);

  const queryParams = {
    view_scope: viewScope,
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

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Indexed media library</span>
        <h3>Image and video records</h3>
      </div>

      <div className="media-library-toolbar">
        <label className="field-stack media-library-toolbar__field">
          <span>Scope</span>
          <select
            className="select-input"
            value={viewScope}
            onChange={(event) => {
              setViewScope(event.target.value as MediaViewScope);
              setPage(1);
            }}
          >
            {VIEW_SCOPE_OPTIONS.map((option) => (
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

      <div className="media-library-meta-row">
        <p>
          {viewScope === "all"
            ? "Showing active indexed image and video files."
            : `Showing active indexed ${viewScope} files.`}
        </p>
        {mediaQuery.data ? <span>{mediaQuery.data.total} media items</span> : null}
      </div>

      {mediaQuery.isLoading ? <p>Loading indexed media...</p> : null}

      {mediaQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Media library failed</strong>
          <p>{mediaQuery.error.message}</p>
        </div>
      ) : null}

      {mediaQuery.data && mediaQuery.data.items.length === 0 ? (
        <div className="future-frame">No active indexed media items are available for this scope yet.</div>
      ) : null}

      {mediaQuery.data && mediaQuery.data.items.length > 0 ? (
        <>
          <div className="media-library-grid">
            {mediaQuery.data.items.map((item) => (
              <button
                key={item.id}
                className={`media-card${selectedItemId === String(item.id) ? " media-card--selected" : ""}`}
                type="button"
                onClick={() => selectItem(String(item.id))}
              >
                <div className="media-card__poster">
                  <span>{item.file_type === "image" ? "Image" : "Video"}</span>
                </div>
                <div className="media-card__body">
                  <strong>{item.name}</strong>
                  <p>{item.path}</p>
                </div>
                <div className="media-card__meta">
                  <span className="status-pill">{item.file_type}</span>
                  <span className="status-pill">{new Date(item.modified_at).toLocaleString()}</span>
                  <span className="status-pill">{formatBytes(item.size_bytes)}</span>
                </div>
              </button>
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
