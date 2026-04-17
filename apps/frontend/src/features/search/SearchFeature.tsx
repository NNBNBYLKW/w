import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import type { ColorTagValue, FileType, SearchSortBy, SearchSortOrder } from "../../entities/file/types";
import { searchFiles } from "../../services/api/searchApi";
import { listTags } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";

const FILE_TYPE_OPTIONS: Array<{ label: string; value: FileType | "all" }> = [
  { label: "All types", value: "all" },
  { label: "Image", value: "image" },
  { label: "Video", value: "video" },
  { label: "Document", value: "document" },
  { label: "Archive", value: "archive" },
  { label: "Other", value: "other" },
];
const COLOR_TAG_OPTIONS: Array<{ label: string; value: ColorTagValue | "all" }> = [
  { label: "All colors", value: "all" },
  { label: "Red", value: "red" },
  { label: "Yellow", value: "yellow" },
  { label: "Green", value: "green" },
  { label: "Blue", value: "blue" },
  { label: "Purple", value: "purple" },
];


export function SearchFeature() {
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
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
        <span className="page-header__eyebrow">Indexed query area</span>
        <h3>Search</h3>
      </div>
      <form className="search-controls" onSubmit={handleSubmit}>
        <div className="search-input-row">
          <input
            className="text-input"
            value={inputQuery}
            onChange={(event) => setInputQuery(event.target.value)}
            placeholder="Search indexed files by name or path"
          />
          <button className="secondary-button" type="submit">
            Search
          </button>
        </div>
        <div className="search-toolbar">
          <label className="field-stack search-toolbar__field">
            <span>Type</span>
            <select
              className="select-input"
              value={fileType}
              onChange={(event) => {
                setFileType(event.target.value as FileType | "all");
                setPage(1);
              }}
            >
              {FILE_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack search-toolbar__field">
            <span>Tag</span>
            <select
              className="select-input"
              value={selectedTagId}
              onChange={(event) => {
                setSelectedTagId(event.target.value);
                setPage(1);
              }}
              disabled={tagsQuery.isLoading || tagsQuery.error instanceof Error}
            >
              <option value="all">{tagsQuery.error instanceof Error ? "Tags unavailable" : "All tags"}</option>
              {(tagsQuery.data?.items ?? []).map((tag) => (
                <option key={tag.id} value={tag.id}>
                  {tag.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack search-toolbar__field">
            <span>Color</span>
            <select
              className="select-input"
              value={selectedColorTag}
              onChange={(event) => {
                setSelectedColorTag(event.target.value as ColorTagValue | "all");
                setPage(1);
              }}
            >
              {COLOR_TAG_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack search-toolbar__field">
            <span>Sort by</span>
            <select
              className="select-input"
              value={sortBy}
              onChange={(event) => {
                setSortBy(event.target.value as SearchSortBy);
                setPage(1);
              }}
            >
              <option value="modified_at">Modified</option>
              <option value="name">Name</option>
              <option value="discovered_at">Discovered</option>
            </select>
          </label>
          <label className="field-stack search-toolbar__field">
            <span>Order</span>
            <select
              className="select-input"
              value={sortOrder}
              onChange={(event) => {
                setSortOrder(event.target.value as SearchSortOrder);
                setPage(1);
              }}
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </label>
        </div>
      </form>

      <div className="search-meta-row">
        <p>
          {appliedQuery ? `Showing matches for "${appliedQuery}".` : "Showing active indexed files for the empty-query state."}
        </p>
        {searchQuery.data ? <span>{searchQuery.data.total} results</span> : null}
      </div>

      {searchQuery.isLoading ? <p>Loading indexed search results...</p> : null}

      {searchQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Search failed</strong>
          <p>{searchQuery.error.message}</p>
        </div>
      ) : null}

      {tagsQuery.error instanceof Error ? (
        <div className="status-block page-card">
          <strong>Tag filters unavailable</strong>
          <p>{tagsQuery.error.message}</p>
        </div>
      ) : null}

      {searchQuery.data && searchQuery.data.items.length === 0 ? (
        <div className="future-frame">No indexed files matched this query yet.</div>
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
