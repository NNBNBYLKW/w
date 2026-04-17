import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import type { FileListSortBy, FileListSortOrder } from "../../entities/file/types";
import { listFilesForTag, listTags, TagsApiError } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}


export function TagBrowserFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const [selectedTagId, setSelectedTagId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [sortBy, setSortBy] = useState<FileListSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");

  const tagsQuery = useQuery({
    queryKey: ["tags"],
    queryFn: listTags,
  });

  useEffect(() => {
    if (!tagsQuery.data) {
      return;
    }

    if (tagsQuery.data.items.length === 0) {
      setSelectedTagId(null);
      return;
    }

    const selectedTagStillExists = selectedTagId !== null && tagsQuery.data.items.some((tag) => tag.id === selectedTagId);
    if (selectedTagStillExists) {
      return;
    }

    setSelectedTagId(tagsQuery.data.items[0].id);
    setPage(1);
  }, [selectedTagId, tagsQuery.data]);

  const tagFilesQueryParams =
    selectedTagId === null
      ? null
      : {
          tagId: selectedTagId,
          page,
          page_size: pageSize,
          sort_by: sortBy,
          sort_order: sortOrder,
        };

  const tagFilesQuery = useQuery({
    queryKey: tagFilesQueryParams ? queryKeys.tagFiles(tagFilesQueryParams) : ["tag-files", "idle"],
    queryFn: () =>
      listFilesForTag(selectedTagId as number, {
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
    enabled: selectedTagId !== null && !(tagsQuery.error instanceof Error),
  });

  const totalPages = tagFilesQuery.data ? Math.max(1, Math.ceil(tagFilesQuery.data.total / tagFilesQuery.data.page_size)) : 1;
  const missingSelectedTag = tagFilesQuery.error instanceof TagsApiError && tagFilesQuery.error.code === "TAG_NOT_FOUND";

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Tag-scoped retrieval</span>
        <h3>Tagged indexed files</h3>
        <p>Use normal tags as a retrieval entry point without expanding into tag-management tooling.</p>
      </div>

      {tagsQuery.isLoading ? <p>Loading tags...</p> : null}

      {tagsQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Tags page unavailable</strong>
          <p>{tagsQuery.error.message}</p>
        </div>
      ) : null}

      {tagsQuery.data && tagsQuery.data.items.length === 0 ? (
        <div className="future-frame">还没有普通标签。请先在详情侧栏给文件添加标签。</div>
      ) : null}

      {tagsQuery.data && tagsQuery.data.items.length > 0 ? (
        <div className="tag-browser-layout">
          <aside className="tag-browser-sidebar">
            <div className="tag-browser-sidebar__header">
              <span className="page-header__eyebrow">Tags</span>
              <p>{tagsQuery.data.items.length} tags</p>
            </div>
            <div className="tag-browser-list">
              {tagsQuery.data.items.map((tag) => (
                <button
                  key={tag.id}
                  className={`tag-browser-list__item${selectedTagId === tag.id ? " tag-browser-list__item--selected" : ""}`}
                  type="button"
                  onClick={() => {
                    setSelectedTagId(tag.id);
                    setPage(1);
                  }}
                >
                  {tag.name}
                </button>
              ))}
            </div>
          </aside>

          <div className="tag-browser-content">
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
              <p>Showing active indexed files attached to the selected normal tag.</p>
              {tagFilesQuery.data ? <span>{tagFilesQuery.data.total} tagged files</span> : null}
            </div>

            {tagFilesQuery.isLoading ? <p>Loading tagged files...</p> : null}

            {missingSelectedTag ? (
              <div className="status-block page-card">
                <strong>Selected tag no longer exists</strong>
                <p>当前标签已不存在，请重新选择标签。</p>
              </div>
            ) : null}

            {!missingSelectedTag && tagFilesQuery.error instanceof Error ? (
              <div className="status-block page-card">
                <strong>Tagged files unavailable</strong>
                <p>{tagFilesQuery.error.message}</p>
              </div>
            ) : null}

            {tagFilesQuery.data && tagFilesQuery.data.items.length === 0 ? (
              <div className="future-frame">No active indexed files are currently attached to this tag.</div>
            ) : null}

            {tagFilesQuery.data && tagFilesQuery.data.items.length > 0 ? (
              <>
                <div className="files-list">
                  {tagFilesQuery.data.items.map((item) => (
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
          </div>
        </div>
      ) : null}
    </section>
  );
}
