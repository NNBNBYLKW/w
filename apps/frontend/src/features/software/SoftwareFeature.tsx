import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import type { FileListSortBy, FileListSortOrder } from "../../entities/file/types";
import { listSoftware } from "../../services/api/softwareApi";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}

function formatSoftwareFormat(value: "exe" | "msi" | "zip"): string {
  return value.toUpperCase();
}


export function SoftwareFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const [sortBy, setSortBy] = useState<FileListSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");
  const [page, setPage] = useState(1);

  const queryParams = {
    page,
    page_size: 50,
    sort_by: sortBy,
    sort_order: sortOrder,
  } as const;

  const softwareQuery = useQuery({
    queryKey: queryKeys.softwareList(queryParams),
    queryFn: () => listSoftware(queryParams),
  });

  const totalPages = softwareQuery.data ? Math.max(1, Math.ceil(softwareQuery.data.total / softwareQuery.data.page_size)) : 1;

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Recognized software-related files</span>
        <h3>Indexed .exe, .msi, and .zip files</h3>
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
      </div>

      <div className="files-meta-row">
        <p>Showing recognized .exe, .msi, and .zip files from the active indexed library.</p>
        {softwareQuery.data ? <span>{softwareQuery.data.total} software-related files</span> : null}
      </div>

      {softwareQuery.isLoading ? <p>Loading recognized software-related files...</p> : null}

      {softwareQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Software listing failed</strong>
          <p>{softwareQuery.error.message}</p>
        </div>
      ) : null}

      {softwareQuery.data && softwareQuery.data.items.length === 0 ? (
        <div className="future-frame">No recognized software-related files are available yet. Scan a source with .exe, .msi, or .zip files to list them here.</div>
      ) : null}

      {softwareQuery.data && softwareQuery.data.items.length > 0 ? (
        <>
          <div className="files-list">
            {softwareQuery.data.items.map((item) => (
              <button
                key={item.id}
                className={`files-list-row${selectedItemId === String(item.id) ? " files-list-row--selected" : ""}`}
                type="button"
                onClick={() => selectItem(String(item.id))}
              >
                <div className="files-list-row__meta">
                  <strong>{item.display_title}</strong>
                  <p>{item.path}</p>
                </div>
                <div className="files-list-row__badges">
                  <span className="status-pill">{formatSoftwareFormat(item.software_format)}</span>
                  <span className="status-pill">{formatBytes(item.size_bytes)}</span>
                  <span className="status-pill">{new Date(item.modified_at).toLocaleString()}</span>
                </div>
              </button>
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
