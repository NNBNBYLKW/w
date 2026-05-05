import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
import type { FileListSortBy, FileListSortOrder } from "../../entities/file/types";
import { listFilesForTag, listTags, TagsApiError } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";


function formatBytes(value: number | null): string {
  return value === null ? t("common.states.sizeUnavailable") : `${value.toLocaleString()} bytes`;
}


export function TagBrowserFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [selectedTagId, setSelectedTagId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [sortBy, setSortBy] = useState<FileListSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");
  const requestedTagId = searchParams.get("tag_id");
  const requestedFocusId = searchParams.get("focus");

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

    if (requestedTagId !== null) {
      const requestedId = Number(requestedTagId);
      if (Number.isInteger(requestedId) && tagsQuery.data.items.some((tag) => tag.id === requestedId)) {
        if (selectedTagId !== requestedId) {
          setSelectedTagId(requestedId);
          setPage(1);
        }
        return;
      }
    }

    const selectedTagStillExists = selectedTagId !== null && tagsQuery.data.items.some((tag) => tag.id === selectedTagId);
    if (selectedTagStillExists) {
      return;
    }

    setSelectedTagId(tagsQuery.data.items[0].id);
    setPage(1);
  }, [requestedTagId, selectedTagId, tagsQuery.data]);

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
  const selectedTag = tagsQuery.data?.items.find((tag) => tag.id === selectedTagId) ?? null;
  const tagFlowNote = requestedFocusId ? t("features.tags.flowNote") : null;

  useEffect(() => {
    if (!requestedFocusId || !tagFilesQuery.data) {
      return;
    }

    const focusedItem = tagFilesQuery.data.items.find((item) => String(item.id) === requestedFocusId);
    if (focusedItem) {
      selectItem(String(focusedItem.id));
    }
  }, [requestedFocusId, selectItem, tagFilesQuery.data]);

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">{t("features.tags.eyebrow")}</span>
        <h3>{t("features.tags.title")}</h3>
        <p>{t("features.tags.description")}</p>
      </div>

      {tagsQuery.isLoading ? <p>{t("features.tags.loading")}</p> : null}

      {tagsQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.tags.unavailableTitle")}</strong>
          <p>{tagsQuery.error.message}</p>
        </div>
      ) : null}

      {tagsQuery.data && tagsQuery.data.items.length === 0 ? (
        <div className="future-frame">{t("features.tags.empty")}</div>
      ) : null}

      {tagsQuery.data && tagsQuery.data.items.length > 0 ? (
        <div className="tag-browser-layout">
          <aside className="tag-browser-sidebar">
            <div className="tag-browser-sidebar__header">
              <span className="page-header__eyebrow">{t("pages.tags.title")}</span>
              <p>{t("common.labels.tags", { count: tagsQuery.data.items.length })}</p>
            </div>
            <div className="tag-browser-list">
              {tagsQuery.data.items.map((tag) => (
                <button
                  key={tag.id}
                  className={`tag-browser-list__item${selectedTagId === tag.id ? " tag-browser-list__item--selected" : ""}`}
                  type="button"
                  title={tag.name}
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

              <div className="files-meta-row">
                <p>{t("features.tags.matchingMeta")}</p>
                <div className="files-meta-row__actions">
                  {tagFilesQuery.data ? <span>{t("common.labels.files", { count: tagFilesQuery.data.total })}</span> : null}
                  {selectedTag ? (
                    <>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => {
                          const params = new URLSearchParams({
                            tag_id: String(selectedTag.id),
                            entry: "tags",
                          });
                          navigate(`/library/media?${params.toString()}`);
                        }}
                      >
                        {t("common.actions.openMatchingMedia")}
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => {
                          const params = new URLSearchParams({
                            tag_id: String(selectedTag.id),
                            entry: "tags",
                          });
                          navigate(`/library/books?${params.toString()}`);
                        }}
                      >
                        {t("common.actions.openMatchingBooks")}
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => {
                          const params = new URLSearchParams({
                            tag_id: String(selectedTag.id),
                            entry: "tags",
                          });
                          navigate(`/library/games?${params.toString()}`);
                        }}
                      >
                        {t("common.actions.openMatchingGames")}
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => {
                          const params = new URLSearchParams({
                            tag_id: String(selectedTag.id),
                            entry: "tags",
                          });
                          navigate(`/software?${params.toString()}`);
                        }}
                      >
                        {t("common.actions.openMatchingSoftware")}
                      </button>
                    </>
                  ) : null}
                </div>
              </div>

            {tagFlowNote ? <div className="context-flow-note">{tagFlowNote}</div> : null}

            {tagFilesQuery.isLoading ? <p>{t("features.tags.loading")}</p> : null}

            {missingSelectedTag ? (
              <div className="status-block page-card">
                <strong>{t("features.tags.selectedTagMissingTitle")}</strong>
                <p>{t("features.tags.selectedTagMissingDescription")}</p>
              </div>
            ) : null}

            {!missingSelectedTag && tagFilesQuery.error instanceof Error ? (
              <div className="status-block page-card">
                <strong>{t("features.tags.matchesUnavailableTitle")}</strong>
                <p>{tagFilesQuery.error.message}</p>
              </div>
            ) : null}

            {tagFilesQuery.data && tagFilesQuery.data.items.length === 0 ? (
              <div className="future-frame">{t("features.tags.noMatches")}</div>
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
                        <strong title={item.name}>{item.name}</strong>
                        <p title={item.path}>{item.path}</p>
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
          </div>
        </div>
      ) : null}
    </section>
  );
}
