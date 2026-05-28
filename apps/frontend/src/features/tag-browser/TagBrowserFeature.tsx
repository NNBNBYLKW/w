import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
import { ConfirmDialog, EmptyState, LoadingState, Pagination, WorkbenchFilterPanel, WorkbenchMasthead, WorkbenchPage, WorkbenchResultFrame, WorkbenchToolbar } from "../../shared/ui/components";
import type { FileListSortBy, FileListSortOrder } from "../../entities/file/types";
import { deleteTagApi, listFilesForTag, listTags, mergeTags, renameTag, TagsApiError } from "../../services/api/tagsApi";
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

  const queryClient = useQueryClient();
  const [renamingTagId, setRenamingTagId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [renameColor, setRenameColor] = useState("");
  const [deleteConfirmTagId, setDeleteConfirmTagId] = useState<number | null>(null);
  const [mergingTagId, setMergingTagId] = useState<number | null>(null);
  const [openMenuTagId, setOpenMenuTagId] = useState<number | null>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  const renameMutation = useMutation({
    mutationFn: ({ tagId, name, color }: { tagId: number; name: string; color?: string | null }) => renameTag(tagId, name, color),
    onSuccess: () => {
      setRenamingTagId(null);
      setRenameValue("");
      setRenameColor("");
      void queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  const deleteTagMutation = useMutation({
    mutationFn: (tagId: number) => deleteTagApi(tagId),
    onSuccess: () => {
      setDeleteConfirmTagId(null);
      if (selectedTagId === deleteConfirmTagId) {
        setSelectedTagId(null);
      }
      void queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  const mergeMutation = useMutation({
    mutationFn: ({ sourceId, targetId }: { sourceId: number; targetId: number }) => mergeTags(sourceId, targetId),
    onSuccess: () => {
      setMergingTagId(null);
      if (selectedTagId === mergingTagId) {
        setSelectedTagId(null);
      }
      void queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  useEffect(() => {
    if (renamingTagId !== null) {
      renameInputRef.current?.focus();
      renameInputRef.current?.select();
    }
  }, [renamingTagId]);

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
    <WorkbenchPage className="refind-surface refind-surface--tags" variant="tags">
      <WorkbenchMasthead
        eyebrow={t("features.tags.eyebrow")}
        title={t("features.tags.title")}
        description={t("features.tags.description")}
      />

      {tagsQuery.isLoading ? <LoadingState /> : null}

      {tagsQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.tags.unavailableTitle")}</strong>
          <p>{tagsQuery.error.message}</p>
        </div>
      ) : null}

      {tagsQuery.data && tagsQuery.data.items.length === 0 ? (
        <EmptyState title={t("features.tags.empty")} description={t("features.tags.emptyGuide")}
          action={{ label: t("features.homeOverview.browseCardAction"), onClick: () => navigate("/browse-v2") }} />
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
                <div key={tag.id} style={{ position: "relative" }}>
                  {renamingTagId === tag.id ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 4, padding: "4px 8px" }}>
                      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                        <input
                          ref={renameInputRef}
                          className="text-input"
                          style={{ flex: 1, fontSize: 13 }}
                          value={renameValue}
                          onChange={(e) => setRenameValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && renameValue.trim()) {
                              renameMutation.mutate({ tagId: tag.id, name: renameValue.trim(), color: renameColor || null });
                            }
                            if (e.key === "Escape") {
                              setRenamingTagId(null);
                              setRenameValue("");
                              setRenameColor("");
                            }
                          }}
                        />
                        <button
                          className="primary-button"
                          style={{ padding: "2px 8px", fontSize: 13 }}
                          type="button"
                          disabled={!renameValue.trim() || renameMutation.isPending}
                          onClick={() => renameMutation.mutate({ tagId: tag.id, name: renameValue.trim(), color: renameColor || null })}
                        >
                          {t("common.actions.save")}
                        </button>
                      </div>
                      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                        <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Color:</span>
                        <input
                          type="color"
                          value={renameColor || "#000000"}
                          onChange={(e) => setRenameColor(e.target.value)}
                          style={{ width: 28, height: 28, padding: 0, border: "none", borderRadius: 4, cursor: "pointer" }}
                        />
                        {renameColor ? (
                          <button
                            type="button"
                            className="ghost-button"
                            style={{ fontSize: 11, padding: "2px 6px" }}
                            onClick={() => setRenameColor("")}
                          >
                            {t("common.actions.clear")}
                          </button>
                        ) : null}
                      </div>
                    </div>
                  ) : (
                    <>
                      <button
                        className={`tag-browser-list__item${selectedTagId === tag.id ? " tag-browser-list__item--selected" : ""}`}
                        type="button"
                        title={tag.name}
                        onClick={() => {
                          setSelectedTagId(tag.id);
                          setPage(1);
                        }}
                      >
                        <span className="tag-color-dot" style={{
                          backgroundColor: tag.color ?? "var(--color-border)",
                          width: 10, height: 10, borderRadius: "50%", display: "inline-block", marginRight: 6,
                          flexShrink: 0,
                        }} />
                        {tag.name}
                      </button>
                      <button
                        type="button"
                        className="tag-browser-list__menu-btn"
                        title={t("common.actions.more")}
                        style={{
                          position: "absolute", right: 4, top: "50%", transform: "translateY(-50%)",
                          background: "none", border: "none", cursor: "pointer", fontSize: 16,
                          lineHeight: 1, padding: "2px 6px", borderRadius: 4,
                          color: "var(--color-text-secondary, #888)",
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpenMenuTagId(openMenuTagId === tag.id ? null : tag.id);
                        }}
                      >
                        ...
                      </button>
                      {openMenuTagId === tag.id ? (
                        <div
                          style={{
                            position: "absolute", right: 0, top: "100%", zIndex: 200,
                            background: "var(--color-surface, #fff)", border: "1px solid var(--color-border, #ddd)",
                            borderRadius: 8, boxShadow: "0 4px 12px rgba(0,0,0,0.1)", minWidth: 120,
                          }}
                          onClick={() => setOpenMenuTagId(null)}
                        >
                          <button
                            type="button"
                            style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px", border: "none", background: "none", cursor: "pointer", fontSize: 13 }}
                            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--color-hover, #f5f5f5)"; }}
                            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = ""; }}
                            onClick={() => {
                              setRenameValue(tag.name);
                              setRenameColor(tag.color ?? "");
                              setRenamingTagId(tag.id);
                            }}
                          >
                            {t("common.actions.rename")}
                          </button>
                          <button
                            type="button"
                            style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px", border: "none", background: "none", cursor: "pointer", fontSize: 13 }}
                            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--color-hover, #f5f5f5)"; }}
                            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = ""; }}
                            onClick={() => setDeleteConfirmTagId(tag.id)}
                          >
                            {t("common.actions.delete")}
                          </button>
                          <button
                            type="button"
                            style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px", border: "none", background: "none", cursor: "pointer", fontSize: 13 }}
                            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--color-hover, #f5f5f5)"; }}
                            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = ""; }}
                            onClick={() => setMergingTagId(tag.id)}
                          >
                            {t("common.actions.merge")}
                          </button>
                        </div>
                      ) : null}
                    </>
                  )}
                </div>
              ))}
            </div>
          </aside>

          <div className="tag-browser-content">
            <WorkbenchFilterPanel className="tag-browser-filter-panel">
              <WorkbenchToolbar className="files-toolbar">
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
              </WorkbenchToolbar>
            </WorkbenchFilterPanel>

              <WorkbenchToolbar className="files-meta-row">
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
                          navigate(`/browse-v2?domain=media&${params.toString()}`);
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
                          navigate(`/browse-v2?domain=documents&${params.toString()}`);
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
                          navigate(`/browse-v2?domain=apps&category=game&${params.toString()}`);
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
                          navigate(`/browse-v2?domain=apps&category=software&${params.toString()}`);
                        }}
                      >
                        {t("common.actions.openMatchingSoftware")}
                      </button>
                    </>
                  ) : null}
                </div>
              </WorkbenchToolbar>

            {tagFlowNote ? <div className="context-flow-note">{tagFlowNote}</div> : null}

            <WorkbenchResultFrame className="tag-browser-result-frame" title={selectedTag?.name ?? t("features.tags.title")}>
            {tagFilesQuery.isLoading ? <LoadingState /> : null}

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
              <EmptyState title={t("features.tags.noMatches")} />
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
                <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
              </>
            ) : null}
            </WorkbenchResultFrame>
          </div>
        </div>
      ) : null}

      {deleteConfirmTagId !== null ? (
        <ConfirmDialog
          open={deleteConfirmTagId !== null}
          title={t("features.tags.deleteConfirmTitle")}
          message={t("features.tags.deleteConfirmMessage")}
          confirmLabel={t("common.actions.delete")}
          onConfirm={() => deleteTagMutation.mutate(deleteConfirmTagId)}
          onCancel={() => setDeleteConfirmTagId(null)}
        />
      ) : null}

      {mergingTagId !== null ? (
        <div
          style={{
            position: "fixed", inset: 0, zIndex: 1000,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: "rgba(0,0,0,0.45)",
          }}
          onClick={() => setMergingTagId(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            style={{
              background: "var(--color-surface, #fff)", borderRadius: 12, width: 400, maxWidth: "90vw",
              padding: 24, boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: "0 0 12px" }}>{t("features.tags.mergeTitle")}</h3>
            <p style={{ margin: "0 0 16px", color: "var(--color-text-secondary, #666)" }}>
              {t("features.tags.mergeDescription")}
            </p>
            <select
              className="select-input"
              style={{ width: "100%", marginBottom: 16 }}
              value=""
              onChange={(e) => {
                const targetId = Number(e.target.value);
                if (targetId && mergingTagId) {
                  mergeMutation.mutate({ sourceId: mergingTagId, targetId });
                }
              }}
            >
              <option value="">{t("features.tags.mergeSelectPlaceholder")}</option>
              {(tagsQuery.data?.items ?? [])
                .filter((tag) => tag.id !== mergingTagId)
                .map((tag) => (
                  <option key={tag.id} value={tag.id}>
                    {tag.name}
                  </option>
                ))}
            </select>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button className="secondary-button" type="button" onClick={() => setMergingTagId(null)}>
                {t("common.actions.cancel")}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {renameMutation.isError && renameMutation.error instanceof Error ? (
        <div className="status-block page-card" style={{ marginTop: 8 }}>
          <strong>{t("features.tags.renameErrorTitle")}</strong>
          <p>{renameMutation.error.message}</p>
        </div>
      ) : null}

      {deleteTagMutation.isError && deleteTagMutation.error instanceof Error ? (
        <div className="status-block page-card" style={{ marginTop: 8 }}>
          <strong>{t("features.tags.deleteErrorTitle")}</strong>
          <p>{deleteTagMutation.error.message}</p>
        </div>
      ) : null}

      {mergeMutation.isError && mergeMutation.error instanceof Error ? (
        <div className="status-block page-card" style={{ marginTop: 8 }}>
          <strong>{t("features.tags.mergeErrorTitle")}</strong>
          <p>{mergeMutation.error.message}</p>
        </div>
      ) : null}
    </WorkbenchPage>
  );
}
