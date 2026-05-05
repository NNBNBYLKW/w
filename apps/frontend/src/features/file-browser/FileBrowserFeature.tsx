import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
import type { ColorTagValue, FileListSortBy, FileListSortOrder, FileType } from "../../entities/file/types";
import { getFileThumbnailUrl } from "../../services/api/fileDetailsApi";
import { listIndexedFiles } from "../../services/api/filesApi";
import { getSources } from "../../services/api/sourcesApi";
import { listTags } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? t("common.states.unavailable") : `${value.toLocaleString()} bytes`;
}

function FileRowThumbnail({ fileId, fileType }: { fileId: number; fileType: FileType }) {
  const [thumbnailFailed, setThumbnailFailed] = useState(false);
  const canLoadThumbnail = (fileType === "image" || fileType === "video") && !thumbnailFailed;

  return (
    <span className={`files-list-row__thumbnail files-list-row__thumbnail--${fileType}`} aria-hidden="true">
      {canLoadThumbnail ? (
        <img
          src={getFileThumbnailUrl(fileId)}
          alt=""
          loading="lazy"
          onError={() => setThumbnailFailed(true)}
        />
      ) : (
        <span>{fileType === "video" ? "VID" : fileType.toUpperCase().slice(0, 3)}</span>
      )}
    </span>
  );
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
  const colorTagOptions: Array<{ label: string; value: ColorTagValue | "all" }> = [
    { label: t("common.colors.all"), value: "all" },
    { label: t("common.colors.red"), value: "red" },
    { label: t("common.colors.yellow"), value: "yellow" },
    { label: t("common.colors.green"), value: "green" },
    { label: t("common.colors.blue"), value: "blue" },
    { label: t("common.colors.purple"), value: "purple" },
  ];
  const [selectedSourceId, setSelectedSourceId] = useState("all");
  const [draftParentPath, setDraftParentPath] = useState("");
  const [appliedParentPath, setAppliedParentPath] = useState<string | null>(null);
  const [browseError, setBrowseError] = useState<string | null>(null);
  const [selectedTagId, setSelectedTagId] = useState("all");
  const [selectedColorTag, setSelectedColorTag] = useState<ColorTagValue | "all">("all");
  const [sortBy, setSortBy] = useState<FileListSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");
  const [page, setPage] = useState(1);
  const sourcesQuery = useQuery({
    queryKey: queryKeys.sources,
    queryFn: getSources,
  });
  const tagsQuery = useQuery({
    queryKey: queryKeys.tags,
    queryFn: listTags,
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
    tag_id: selectedTagId === "all" ? undefined : Number(selectedTagId),
    color_tag: selectedColorTag === "all" ? undefined : selectedColorTag,
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
      setBrowseError(t("features.files.withinSourceError"));
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
            <p>{t("features.files.exactDirectoryRootEmpty")}</p>
          ) : (
            <p>{t("features.files.exactDirectoryEmpty")}</p>
          )}
        </div>
      );
    } else {
      emptyState = <div className="future-frame">{t("features.files.empty")}</div>;
    }
  }

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">{t("features.files.eyebrow")}</span>
        <h3>{t("features.files.title")}</h3>
      </div>

      <div className="files-toolbar">
        <label className="field-stack files-toolbar__field">
          <span>{t("common.labels.source")}</span>
          <select
            className="select-input"
            value={selectedSourceId}
            onChange={(event) => handleSourceChange(event.target.value)}
          >
            <option value="all">{t("features.files.sourceAll")}</option>
            {(sourcesQuery.data ?? []).map((source) => (
              <option key={source.id} value={source.id}>
                {source.display_name ?? source.path}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack files-toolbar__field">
          <span>{t("common.labels.sortBy")}</span>
          <select
            className="select-input"
            value={sortBy}
            onChange={(event) => {
              setSortBy(event.target.value as FileListSortBy);
              setPage(1);
            }}
          >
            <option value="modified_at">{t("common.sortBy.modified")}</option>
            <option value="name">{t("common.sortBy.name")}</option>
            <option value="discovered_at">{t("common.sortBy.discovered")}</option>
            </select>
          </label>
        <label className="field-stack files-toolbar__field">
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
        <label className="field-stack files-toolbar__field">
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
        <label className="field-stack files-toolbar__field">
          <span>{t("common.labels.order")}</span>
          <select
            className="select-input"
            value={sortOrder}
            onChange={(event) => {
              setSortOrder(event.target.value as FileListSortOrder);
              setPage(1);
            }}
          >
            <option value="desc">{t("common.sortOrder.descending")}</option>
            <option value="asc">{t("common.sortOrder.ascending")}</option>
          </select>
          </label>
        </div>

      {selectedSourceRoot !== null ? (
        <section className="files-path-section">
          <div className="files-path-section__copy">
            <span className="page-header__eyebrow">{t("features.files.exactBrowsingEyebrow")}</span>
            <p>{t("features.files.exactBrowsingDescription")}</p>
          </div>
          <form
            className="files-path-form"
            onSubmit={(event) => {
              event.preventDefault();
              applyDraftParentPath();
            }}
          >
            <label className="field-stack files-path-form__field">
              <span>{t("common.labels.currentDirectory")}</span>
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
                {t("common.actions.root")}
              </button>
              <button className="secondary-button" type="button" onClick={goUpOneDirectory}>
                {t("common.actions.up")}
              </button>
              <button className="secondary-button" type="submit">
                {t("common.actions.browse")}
              </button>
            </div>
          </form>
          {browseError ? <p className="files-path-section__error">{browseError}</p> : null}
        </section>
      ) : null}

      <div className="files-meta-row">
        <p>
          {selectedSourceRoot !== null
            ? t("features.files.currentDirectoryMeta")
            : t("features.files.globalMeta")}
        </p>
        {filesQuery.data ? <span>{t("common.labels.indexedFiles", { count: filesQuery.data.total })}</span> : null}
      </div>

      {filesQuery.isLoading ? <p>{t("features.files.loading")}</p> : null}

      {sourcesQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.files.sourceUnavailableTitle")}</strong>
          <p>{sourcesQuery.error.message}</p>
        </div>
      ) : null}

      {tagsQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.files.tagUnavailableTitle")}</strong>
          <p>{tagsQuery.error.message}</p>
        </div>
      ) : null}

      {filesQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.files.failedTitle")}</strong>
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
                <FileRowThumbnail fileId={item.id} fileType={item.file_type} />
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
