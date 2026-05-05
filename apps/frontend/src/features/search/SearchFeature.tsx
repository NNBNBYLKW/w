import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
import type { ColorTagValue, FileType, SearchSortBy, SearchSortOrder } from "../../entities/file/types";
import { searchFiles } from "../../services/api/searchApi";
import { listTags } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";


export function SearchFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const fileTypeOptions: Array<{ label: string; value: FileType | "all" }> = [
    { label: t("common.fileTypes.all"), value: "all" },
    { label: t("common.fileTypes.image"), value: "image" },
    { label: t("common.fileTypes.video"), value: "video" },
    { label: t("common.fileTypes.document"), value: "document" },
    { label: t("common.fileTypes.archive"), value: "archive" },
    { label: t("common.fileTypes.other"), value: "other" },
  ];
  const colorTagOptions: Array<{ label: string; value: ColorTagValue | "all" }> = [
    { label: t("common.colors.all"), value: "all" },
    { label: t("common.colors.red"), value: "red" },
    { label: t("common.colors.yellow"), value: "yellow" },
    { label: t("common.colors.green"), value: "green" },
    { label: t("common.colors.blue"), value: "blue" },
    { label: t("common.colors.purple"), value: "purple" },
  ];
  const [inputQuery, setInputQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [fileType, setFileType] = useState<FileType | "all">("all");
  const [selectedTagId, setSelectedTagId] = useState("all");
  const [selectedColorTag, setSelectedColorTag] = useState<ColorTagValue | "all">("all");
  const [sortBy, setSortBy] = useState<SearchSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<SearchSortOrder>("desc");
  const [page, setPage] = useState(1);
  const tagsQuery = useQuery({
    queryKey: queryKeys.tags,
    queryFn: listTags,
  });

  const queryParams = {
    query: appliedQuery,
    file_type: fileType === "all" ? undefined : fileType,
    tag_id: selectedTagId === "all" ? undefined : Number(selectedTagId),
    color_tag: selectedColorTag === "all" ? undefined : selectedColorTag,
    page,
    page_size: 50,
    sort_by: sortBy,
    sort_order: sortOrder,
  } as const;

  const searchQuery = useQuery({
    queryKey: queryKeys.search(queryParams),
    queryFn: () => searchFiles(queryParams),
  });

  const totalPages = searchQuery.data ? Math.max(1, Math.ceil(searchQuery.data.total / searchQuery.data.page_size)) : 1;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAppliedQuery(inputQuery.trim());
    setPage(1);
  };

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">{t("features.search.eyebrow")}</span>
        <h3>{t("features.search.title")}</h3>
      </div>
      <form className="search-controls" onSubmit={handleSubmit}>
        <div className="search-input-row">
          <input
            className="text-input"
            value={inputQuery}
            onChange={(event) => setInputQuery(event.target.value)}
            placeholder={t("features.search.placeholder")}
          />
          <button className="secondary-button" type="submit">
            {t("common.actions.search")}
          </button>
        </div>
        <div className="search-toolbar">
          <label className="field-stack search-toolbar__field">
            <span>{t("common.labels.type")}</span>
            <select
              className="select-input"
              value={fileType}
              onChange={(event) => {
                setFileType(event.target.value as FileType | "all");
                setPage(1);
              }}
            >
              {fileTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack search-toolbar__field">
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
          <label className="field-stack search-toolbar__field">
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
          <label className="field-stack search-toolbar__field">
            <span>{t("common.labels.sortBy")}</span>
            <select
              className="select-input"
              value={sortBy}
              onChange={(event) => {
                setSortBy(event.target.value as SearchSortBy);
                setPage(1);
              }}
            >
              <option value="modified_at">{t("common.sortBy.modified")}</option>
              <option value="name">{t("common.sortBy.name")}</option>
              <option value="discovered_at">{t("common.sortBy.discovered")}</option>
            </select>
          </label>
          <label className="field-stack search-toolbar__field">
            <span>{t("common.labels.order")}</span>
            <select
              className="select-input"
              value={sortOrder}
              onChange={(event) => {
                setSortOrder(event.target.value as SearchSortOrder);
                setPage(1);
              }}
            >
              <option value="desc">{t("common.sortOrder.descending")}</option>
              <option value="asc">{t("common.sortOrder.ascending")}</option>
            </select>
          </label>
        </div>
      </form>

      <div className="search-meta-row">
        <p>
          {appliedQuery ? t("features.search.matches", { query: appliedQuery }) : t("features.search.emptyQuery")}
        </p>
        {searchQuery.data ? <span>{t("common.labels.results", { count: searchQuery.data.total })}</span> : null}
      </div>

      {searchQuery.isLoading ? <p>{t("features.search.loading")}</p> : null}

      {searchQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.search.failedTitle")}</strong>
          <p>{searchQuery.error.message}</p>
        </div>
      ) : null}

      {tagsQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>{t("features.search.tagsUnavailableTitle")}</strong>
          <p>{tagsQuery.error.message}</p>
        </div>
      ) : null}

      {searchQuery.data && searchQuery.data.items.length === 0 ? (
        <div className="future-frame">{t("features.search.empty")}</div>
      ) : null}

      {searchQuery.data && searchQuery.data.items.length > 0 ? (
        <>
          <div className="search-results">
            {searchQuery.data.items.map((item) => (
              <button
                key={item.id}
                className={`search-result-row${selectedItemId === String(item.id) ? " search-result-row--selected" : ""}`}
                type="button"
                onClick={() => selectItem(String(item.id))}
              >
                <div className="search-result-row__meta">
                  <strong>{item.name}</strong>
                  <p>{item.path}</p>
                </div>
                <div className="search-result-row__badges">
                  <span className="status-pill">{item.file_type}</span>
                  <span className="status-pill">{new Date(item.modified_at).toLocaleString()}</span>
                </div>
              </button>
            ))}
          </div>
          <div className="search-pager">
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
