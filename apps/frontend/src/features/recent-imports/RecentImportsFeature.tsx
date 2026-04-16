import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import type { FileListSortOrder } from "../../entities/file/types";
import type { RecentRangeValue } from "../../entities/recent/types";
import { listRecentImports } from "../../services/api/recentApi";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}


const RANGE_OPTIONS: Array<{ label: string; hint: string; value: RecentRangeValue }> = [
  { label: "1 day", hint: "Last 1 day", value: "1d" },
  { label: "7 days", hint: "Last 7 days", value: "7d" },
  { label: "30 days", hint: "Last 30 days", value: "30d" },
];


export function RecentImportsFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const [range, setRange] = useState<RecentRangeValue>("7d");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");
  const [page, setPage] = useState(1);

  const selectedRangeLabel = RANGE_OPTIONS.find((option) => option.value === range)?.hint ?? "Last 7 days";
  const queryParams = {
    range,
    page,
    page_size: 50,
    sort_order: sortOrder,
  } as const;

  const recentQuery = useQuery({
    queryKey: queryKeys.recent(queryParams),
    queryFn: () => listRecentImports(queryParams),
  });

  const totalPages = recentQuery.data ? Math.max(1, Math.ceil(recentQuery.data.total / recentQuery.data.page_size)) : 1;

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Recent-imports listing</span>
        <h3>Recently indexed files</h3>
      </div>

      <div className="recent-toolbar">
        <div className="recent-range-switch" aria-label="Recent import range">
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
        <p>Showing active indexed files first discovered in the selected recent-import window: {selectedRangeLabel}.</p>
        {recentQuery.data ? <span>{recentQuery.data.total} recently indexed files</span> : null}
      </div>

      {recentQuery.isLoading ? <p>Loading recently indexed files...</p> : null}

      {recentQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Recent imports failed</strong>
          <p>{recentQuery.error.message}</p>
        </div>
      ) : null}

      {recentQuery.data && recentQuery.data.items.length === 0 ? (
        <div className="future-frame">No active indexed files were discovered in this recent-import window yet.</div>
      ) : null}

      {recentQuery.data && recentQuery.data.items.length > 0 ? (
        <>
          <div className="recent-list">
            {recentQuery.data.items.map((item) => (
              <button
                key={item.id}
                className={`recent-row${selectedItemId === String(item.id) ? " recent-row--selected" : ""}`}
                type="button"
                onClick={() => selectItem(String(item.id))}
              >
                <div className="recent-row__meta">
                  <strong>{item.name}</strong>
                  <p>{item.path}</p>
                </div>
                <div className="recent-row__badges">
                  <span className="status-pill">{item.file_type}</span>
                  <span className="status-pill">{new Date(item.discovered_at).toLocaleString()}</span>
                  <span className="status-pill">{formatBytes(item.size_bytes)}</span>
                </div>
              </button>
            ))}
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
