import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import type { FileListSortBy, FileListSortOrder } from "../../entities/file/types";
import { listIndexedFiles } from "../../services/api/filesApi";
import { getSources } from "../../services/api/sourcesApi";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}


function isDriveRoot(value: string): boolean {
  return /^[A-Za-z]:\\$/.test(value);
}


function normalizeDirectoryPath(value: string): string {
  const normalized = value.trim().replace(/\//g, "\\");
  if (!normalized) {
    return "";
  }
  if (isDriveRoot(normalized)) {
    return normalized;
  }
  return normalized.replace(/\\+$/g, "");
}


function isWithinSourceRoot(candidatePath: string, sourceRoot: string): boolean {
  const normalizedCandidate = normalizeDirectoryPath(candidatePath).toLowerCase();
  const normalizedSourceRoot = normalizeDirectoryPath(sourceRoot).toLowerCase();

  if (normalizedCandidate === normalizedSourceRoot) {
    return true;
  }
  if (isDriveRoot(normalizeDirectoryPath(sourceRoot))) {
    return normalizedCandidate.startsWith(normalizedSourceRoot);
  }
  return normalizedCandidate.startsWith(`${normalizedSourceRoot}\\`);
}


function getParentDirectoryPath(path: string): string {
  const normalizedPath = normalizeDirectoryPath(path);
  if (!normalizedPath || isDriveRoot(normalizedPath)) {
    return normalizedPath;
  }

  const lastSeparatorIndex = normalizedPath.lastIndexOf("\\");
  if (lastSeparatorIndex === 2 && normalizedPath[1] === ":") {
    return normalizedPath.slice(0, 3);
  }

  return normalizedPath.slice(0, lastSeparatorIndex);
}


export function FileBrowserFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const [selectedSourceId, setSelectedSourceId] = useState("all");
  const [draftParentPath, setDraftParentPath] = useState("");
  const [appliedParentPath, setAppliedParentPath] = useState<string | null>(null);
  const [browseError, setBrowseError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<FileListSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");
  const [page, setPage] = useState(1);
  const sourcesQuery = useQuery({
    queryKey: queryKeys.sources,
    queryFn: getSources,
  });
  const selectedSource =
    selectedSourceId === "all"
      ? null
      : sourcesQuery.data?.find((source) => String(source.id) === selectedSourceId) ?? null;
  const selectedSourceRoot = selectedSource ? normalizeDirectoryPath(selectedSource.path) : null;
  const currentDirectoryPath =
    selectedSource !== null ? appliedParentPath ?? selectedSourceRoot : null;

  const queryParams = {
    source_id: selectedSource?.id,
    parent_path: currentDirectoryPath ?? undefined,
    page,
    page_size: 50,
    sort_by: sortBy,
    sort_order: sortOrder,
  } as const;

  const filesQuery = useQuery({
    queryKey: queryKeys.filesList(queryParams),
    queryFn: () => listIndexedFiles(queryParams),
  });

  const totalPages = filesQuery.data ? Math.max(1, Math.ceil(filesQuery.data.total / filesQuery.data.page_size)) : 1;

  const isAtSourceRoot =
    selectedSourceRoot !== null &&
    currentDirectoryPath !== null &&
    currentDirectoryPath.toLowerCase() === selectedSourceRoot.toLowerCase();

  const handleSourceChange = (value: string) => {
    setSelectedSourceId(value);
    setBrowseError(null);
    setPage(1);

    if (value === "all") {
      setDraftParentPath("");
      setAppliedParentPath(null);
      return;
    }

    const source = sourcesQuery.data?.find((item) => String(item.id) === value);
    if (!source) {
      setDraftParentPath("");
      setAppliedParentPath(null);
      return;
    }

    const rootPath = normalizeDirectoryPath(source.path);
    setDraftParentPath(rootPath);
    setAppliedParentPath(rootPath);
  };

  const applyDraftParentPath = () => {
    if (selectedSourceRoot === null) {
      return;
    }

    const normalizedPath = normalizeDirectoryPath(draftParentPath) || selectedSourceRoot;
    if (!isWithinSourceRoot(normalizedPath, selectedSourceRoot)) {
      setBrowseError("The current directory must stay within the selected source root.");
      return;
    }

    setBrowseError(null);
    setDraftParentPath(normalizedPath);
    setAppliedParentPath(normalizedPath);
    setPage(1);
  };

  const goToSourceRoot = () => {
    if (selectedSourceRoot === null) {
      return;
    }
    setBrowseError(null);
    setDraftParentPath(selectedSourceRoot);
    setAppliedParentPath(selectedSourceRoot);
    setPage(1);
  };

  const goUpOneDirectory = () => {
    if (selectedSourceRoot === null || currentDirectoryPath === null) {
      return;
    }
    if (currentDirectoryPath.toLowerCase() === selectedSourceRoot.toLowerCase()) {
      setBrowseError(null);
      return;
    }

    const nextPath = getParentDirectoryPath(currentDirectoryPath);
    const clampedPath = isWithinSourceRoot(nextPath, selectedSourceRoot) ? nextPath : selectedSourceRoot;
    setBrowseError(null);
    setDraftParentPath(clampedPath);
    setAppliedParentPath(clampedPath);
    setPage(1);
  };

  let emptyState: JSX.Element | null = null;
  if (filesQuery.data && filesQuery.data.items.length === 0) {
    if (selectedSourceRoot !== null) {
      emptyState = (
        <div className="future-frame">
          {isAtSourceRoot ? (
            <p>
              This exact-directory view only shows files directly inside the selected source root. No directly indexed
              files were found here yet, so browse a deeper path manually.
            </p>
          ) : (
            <p>
              This exact-directory view only shows files directly inside the current directory. Browse a different
              exact path manually or move up to another directory.
            </p>
          )}
        </div>
      );
    } else {
      emptyState = <div className="future-frame">No active indexed files are available yet.</div>;
    }
  }

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Flat indexed-files listing</span>
        <h3>Indexed file records</h3>
      </div>

      <div className="files-toolbar">
        <label className="field-stack files-toolbar__field">
          <span>Source</span>
          <select
            className="select-input"
            value={selectedSourceId}
            onChange={(event) => handleSourceChange(event.target.value)}
          >
            <option value="all">All indexed files</option>
            {(sourcesQuery.data ?? []).map((source) => (
              <option key={source.id} value={source.id}>
                {source.display_name ?? source.path}
              </option>
            ))}
          </select>
        </label>
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

      {selectedSourceRoot !== null ? (
        <section className="files-path-section">
          <div className="files-path-section__copy">
            <span className="page-header__eyebrow">Exact directory browsing</span>
            <p>Browse one exact indexed directory at a time. This is not a tree or breadcrumb view.</p>
          </div>
          <form
            className="files-path-form"
            onSubmit={(event) => {
              event.preventDefault();
              applyDraftParentPath();
            }}
          >
            <label className="field-stack files-path-form__field">
              <span>Current directory</span>
              <input
                className="text-input"
                value={draftParentPath}
                onChange={(event) => {
                  setDraftParentPath(event.target.value);
                  setBrowseError(null);
                }}
                placeholder={selectedSourceRoot}
              />
            </label>
            <div className="files-path-actions">
              <button className="secondary-button" type="button" onClick={goToSourceRoot}>
                Root
              </button>
              <button className="secondary-button" type="button" onClick={goUpOneDirectory}>
                Up
              </button>
              <button className="secondary-button" type="submit">
                Browse
              </button>
            </div>
          </form>
          {browseError ? <p className="files-path-section__error">{browseError}</p> : null}
        </section>
      ) : null}

      <div className="files-meta-row">
        <p>
          {selectedSourceRoot !== null
            ? "Showing active indexed file records for the current exact directory."
            : "Showing active indexed file records."}
        </p>
        {filesQuery.data ? <span>{filesQuery.data.total} indexed files</span> : null}
      </div>

      {filesQuery.isLoading ? <p>Loading indexed files...</p> : null}

      {sourcesQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Source list unavailable</strong>
          <p>{sourcesQuery.error.message}</p>
        </div>
      ) : null}

      {filesQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Files listing failed</strong>
          <p>{filesQuery.error.message}</p>
        </div>
      ) : null}

      {emptyState}

      {filesQuery.data && filesQuery.data.items.length > 0 ? (
        <>
          <div className="files-list">
            {filesQuery.data.items.map((item) => (
              <button
                key={item.id}
                className={`files-list-row${selectedItemId === String(item.id) ? " files-list-row--selected" : ""}`}
                type="button"
                onClick={() => selectItem(String(item.id))}
              >
                <div className="files-list-row__meta">
                  <strong>{item.name}</strong>
                  <p>{item.path}</p>
                </div>
                <div className="files-list-row__badges">
                  <span className="status-pill">{item.file_type}</span>
                  <span className="status-pill">{new Date(item.modified_at).toLocaleString()}</span>
                  <span className="status-pill">{formatBytes(item.size_bytes)}</span>
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
