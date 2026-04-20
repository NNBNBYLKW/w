import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import type { FileListSortBy, FileListSortOrder } from "../../entities/file/types";
import { listBooks } from "../../services/api/booksApi";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}

function formatBookFormat(value: "epub" | "pdf"): string {
  return value.toUpperCase();
}


export function BooksFeature() {
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

  const booksQuery = useQuery({
    queryKey: queryKeys.booksList(queryParams),
    queryFn: () => listBooks(queryParams),
  });

  const totalPages = booksQuery.data ? Math.max(1, Math.ceil(booksQuery.data.total / booksQuery.data.page_size)) : 1;
  const hasNoRecognizedBooks = booksQuery.data !== undefined && booksQuery.data.total === 0;
  const hasNoCurrentPageResults = booksQuery.data !== undefined && booksQuery.data.total > 0 && booksQuery.data.items.length === 0;

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Indexed ebook records</span>
        <h3>Recognized .epub and .pdf files</h3>
        <p>Select a row to open the shared indexed-file details and actions. Use Search for broader retrieval and Collections for saved retrieval.</p>
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
        <p>Showing recognized .epub and .pdf files from the active indexed library. This surface stays focused on the ebook subset only.</p>
        {booksQuery.data ? <span>{booksQuery.data.total} ebook files</span> : null}
      </div>

      {booksQuery.isLoading ? <p>Loading recognized ebook files...</p> : null}

      {booksQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Books listing failed</strong>
          <p>{booksQuery.error.message}</p>
        </div>
      ) : null}

      {hasNoRecognizedBooks ? (
        <div className="future-frame">No recognized ebook files are available yet. Books only lists indexed .epub and .pdf files, so add a source and run a scan first.</div>
      ) : null}

      {hasNoCurrentPageResults ? (
        <div className="future-frame">Recognized ebook files are available, but none appear on the current page. Return to a previous page to keep browsing this subset list.</div>
      ) : null}

      {booksQuery.data && booksQuery.data.items.length > 0 ? (
        <>
          <div className="files-list">
            {booksQuery.data.items.map((item) => (
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
                  <span className="status-pill">{formatBookFormat(item.book_format)}</span>
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
