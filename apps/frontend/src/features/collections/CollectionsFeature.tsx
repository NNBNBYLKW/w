import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import type { CollectionVM, CreateCollectionInput } from "../../entities/collection/types";
import type { ColorTagValue, FileListSortBy, FileListSortOrder, FileType } from "../../entities/file/types";
import type { SourceVM } from "../../entities/source/types";
import type { TagItemVM } from "../../entities/tag/types";
import { createCollection, deleteCollection, CollectionsApiError, listCollectionFiles, listCollections } from "../../services/api/collectionsApi";
import { getSources } from "../../services/api/sourcesApi";
import { listTags } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";


const COLOR_TAG_OPTIONS: Array<{ label: string; value: ColorTagValue }> = [
  { label: "Red", value: "red" },
  { label: "Yellow", value: "yellow" },
  { label: "Green", value: "green" },
  { label: "Blue", value: "blue" },
  { label: "Purple", value: "purple" },
];

const FILE_TYPE_OPTIONS: Array<{ label: string; value: FileType }> = [
  { label: "Image", value: "image" },
  { label: "Video", value: "video" },
  { label: "Document", value: "document" },
  { label: "Archive", value: "archive" },
  { label: "Other", value: "other" },
];


function formatBytes(value: number | null): string {
  return value === null ? "Size unavailable" : `${value.toLocaleString()} bytes`;
}

function getTagLabel(tagId: number | null, tags: TagItemVM[] | undefined): string | null {
  if (tagId === null) {
    return null;
  }
  const match = tags?.find((tag) => tag.id === tagId);
  return match?.name ?? `Tag #${tagId}`;
}

function getSourceLabel(sourceId: number | null, sources: SourceVM[] | undefined): string | null {
  if (sourceId === null) {
    return null;
  }
  const match = sources?.find((source) => source.id === sourceId);
  if (!match) {
    return `Source #${sourceId}`;
  }
  return match.display_name?.trim() || match.path;
}

function buildCollectionSummary(collection: CollectionVM, tags: TagItemVM[] | undefined, sources: SourceVM[] | undefined): string {
  const parts: string[] = [];

  if (collection.file_type) {
    parts.push(`Type: ${collection.file_type}`);
  }

  const tagLabel = getTagLabel(collection.tag_id, tags);
  if (tagLabel) {
    parts.push(`Tag: ${tagLabel}`);
  }

  if (collection.color_tag) {
    parts.push(`Color: ${collection.color_tag}`);
  }

  const sourceLabel = getSourceLabel(collection.source_id, sources);
  if (sourceLabel) {
    parts.push(`Source: ${sourceLabel}`);
  }

  if (collection.parent_path) {
    parts.push(`Path: ${collection.parent_path}`);
  }

  return parts.length > 0 ? parts.join(" | ") : "All active indexed files";
}


export function CollectionsFeature() {
  const queryClient = useQueryClient();
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);

  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<FileListSortBy>("modified_at");
  const [sortOrder, setSortOrder] = useState<FileListSortOrder>("desc");

  const [name, setName] = useState("");
  const [fileType, setFileType] = useState<FileType | "">("");
  const [tagId, setTagId] = useState<string>("");
  const [colorTag, setColorTag] = useState<ColorTagValue | "">("");
  const [sourceId, setSourceId] = useState<string>("");
  const [parentPath, setParentPath] = useState("");

  const collectionsQuery = useQuery({
    queryKey: queryKeys.collections,
    queryFn: listCollections,
  });

  const tagsQuery = useQuery({
    queryKey: queryKeys.tags,
    queryFn: listTags,
  });

  const sourcesQuery = useQuery({
    queryKey: queryKeys.sources,
    queryFn: getSources,
  });

  useEffect(() => {
    if (!collectionsQuery.data) {
      return;
    }

    if (collectionsQuery.data.items.length === 0) {
      setSelectedCollectionId(null);
      setPage(1);
      return;
    }

    const selectedStillExists =
      selectedCollectionId !== null && collectionsQuery.data.items.some((item) => item.id === selectedCollectionId);
    if (selectedStillExists) {
      return;
    }

    setSelectedCollectionId(collectionsQuery.data.items[0].id);
    setPage(1);
  }, [collectionsQuery.data, selectedCollectionId]);

  const selectedCollection = useMemo(
    () => collectionsQuery.data?.items.find((item) => item.id === selectedCollectionId) ?? null,
    [collectionsQuery.data, selectedCollectionId],
  );

  const collectionFilesQueryParams =
    selectedCollectionId === null
      ? null
      : {
          collectionId: selectedCollectionId,
          page,
          page_size: 50,
          sort_by: sortBy,
          sort_order: sortOrder,
        };

  const collectionFilesQuery = useQuery({
    queryKey: collectionFilesQueryParams ? queryKeys.collectionFiles(collectionFilesQueryParams) : ["collection-files", "idle"],
    queryFn: () => listCollectionFiles(collectionFilesQueryParams as NonNullable<typeof collectionFilesQueryParams>),
    enabled: selectedCollectionId !== null && !(collectionsQuery.error instanceof Error),
  });

  const createCollectionMutation = useMutation({
    mutationFn: (input: CreateCollectionInput) => createCollection(input),
    onSuccess: async (createdCollection) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.collections });
      setSelectedCollectionId(createdCollection.id);
      setPage(1);
      setName("");
      setFileType("");
      setTagId("");
      setColorTag("");
      setSourceId("");
      setParentPath("");
    },
  });

  const deleteCollectionMutation = useMutation({
    mutationFn: (collectionId: number) => deleteCollection(collectionId),
    onSuccess: async (_, deletedCollectionId) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.collections });
      await queryClient.invalidateQueries({ queryKey: ["collection-files"] });

      if (selectedCollectionId === deletedCollectionId) {
        setPage(1);
      }
    },
  });

  const totalPages = collectionFilesQuery.data
    ? Math.max(1, Math.ceil(collectionFilesQuery.data.total / collectionFilesQuery.data.page_size))
    : 1;

  const canChooseTags = !(tagsQuery.error instanceof Error);
  const canChooseSources = !(sourcesQuery.error instanceof Error);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const payload: CreateCollectionInput = {
      name,
    };

    if (fileType) {
      payload.file_type = fileType;
    }
    if (tagId) {
      payload.tag_id = Number(tagId);
    }
    if (colorTag) {
      payload.color_tag = colorTag;
    }
    if (sourceId) {
      payload.source_id = Number(sourceId);
    }
    if (parentPath.trim()) {
      payload.parent_path = parentPath.trim();
    }

    createCollectionMutation.mutate(payload);
  };

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Saved collections</span>
        <h3>Reusable file retrieval</h3>
        <p>Save a narrow set of structured retrieval conditions here and keep using the shared details panel for inspection and actions.</p>
      </div>

      <div className="collections-layout">
        <aside className="collections-sidebar">
          <form className="form-grid collections-form" onSubmit={handleSubmit}>
            <div className="collections-form__header">
              <span className="page-header__eyebrow">Create collection</span>
              <p>Store a minimal file retrieval condition set.</p>
            </div>

            <label className="field-stack">
              <span>Name</span>
              <input
                className="text-input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Blue Images"
              />
            </label>

            <label className="field-stack">
              <span>File type</span>
              <select className="select-input" value={fileType} onChange={(event) => setFileType(event.target.value as FileType | "")}>
                <option value="">Any type</option>
                {FILE_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field-stack">
              <span>Tag</span>
              <select
                className="select-input"
                value={tagId}
                onChange={(event) => setTagId(event.target.value)}
                disabled={tagsQuery.isLoading || !canChooseTags}
              >
                <option value="">Any tag</option>
                {tagsQuery.data?.items.map((tag) => (
                  <option key={tag.id} value={String(tag.id)}>
                    {tag.name}
                  </option>
                ))}
              </select>
            </label>

            {tagsQuery.error instanceof Error ? <p className="collections-form__note">Tags unavailable. Collection creation can continue without a tag filter.</p> : null}

            <label className="field-stack">
              <span>Color tag</span>
              <select
                className="select-input"
                value={colorTag}
                onChange={(event) => setColorTag(event.target.value as ColorTagValue | "")}
              >
                <option value="">Any color</option>
                {COLOR_TAG_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field-stack">
              <span>Source</span>
              <select
                className="select-input"
                value={sourceId}
                onChange={(event) => {
                  const nextSourceId = event.target.value;
                  setSourceId(nextSourceId);
                  if (!nextSourceId) {
                    setParentPath("");
                  }
                }}
                disabled={sourcesQuery.isLoading || !canChooseSources}
              >
                <option value="">Any source</option>
                {sourcesQuery.data?.map((source) => (
                  <option key={source.id} value={String(source.id)}>
                    {source.display_name?.trim() || source.path}
                  </option>
                ))}
              </select>
            </label>

            {sourcesQuery.error instanceof Error ? <p className="collections-form__note">Sources unavailable. Collection creation can continue without a source filter.</p> : null}

            <label className="field-stack">
              <span>Parent path</span>
              <input
                className="text-input"
                value={parentPath}
                onChange={(event) => setParentPath(event.target.value)}
                placeholder="D:\\Assets\\Refs"
                disabled={!sourceId}
              />
            </label>

            {createCollectionMutation.error instanceof Error ? (
              <p className="collections-form__error">{createCollectionMutation.error.message}</p>
            ) : null}

            <div className="collections-form__actions">
              <button className="primary-button" type="submit" disabled={createCollectionMutation.isPending}>
                {createCollectionMutation.isPending ? "Saving..." : "Create collection"}
              </button>
            </div>
          </form>

          <div className="collections-list-shell">
            <div className="collections-list-shell__header">
              <span className="page-header__eyebrow">Collections</span>
              {collectionsQuery.data ? <p>{collectionsQuery.data.items.length} saved collections</p> : <p>Saved reusable entry points</p>}
            </div>

            {collectionsQuery.isLoading ? <p>Loading collections...</p> : null}

            {collectionsQuery.error instanceof Error ? (
              <div className="status-block page-card">
                <strong>Collections unavailable</strong>
                <p>{collectionsQuery.error.message}</p>
              </div>
            ) : null}

            {collectionsQuery.data && collectionsQuery.data.items.length === 0 ? (
              <div className="future-frame">No saved collections yet. Create one to reuse a narrow retrieval condition set.</div>
            ) : null}

            {collectionsQuery.data && collectionsQuery.data.items.length > 0 ? (
              <div className="collections-list">
                {collectionsQuery.data.items.map((collection) => (
                  <div
                    key={collection.id}
                    className={`collections-list__item${selectedCollectionId === collection.id ? " collections-list__item--selected" : ""}`}
                  >
                    <button
                      className="collections-list__select"
                      type="button"
                      onClick={() => {
                        setSelectedCollectionId(collection.id);
                        setPage(1);
                      }}
                    >
                      <div className="collections-list__meta">
                        <strong>{collection.name}</strong>
                        <p>{buildCollectionSummary(collection, tagsQuery.data?.items, sourcesQuery.data)}</p>
                      </div>
                    </button>
                    <div className="collections-list__actions">
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => {
                          deleteCollectionMutation.mutate(collection.id);
                        }}
                        disabled={deleteCollectionMutation.isPending}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </aside>

        <div className="collections-results">
          <div className="collections-results__header">
            <div className="feature-header">
              <span className="page-header__eyebrow">Collection results</span>
              <h3>{selectedCollection?.name ?? "Choose a collection"}</h3>
              <p>
                {selectedCollection
                  ? buildCollectionSummary(selectedCollection, tagsQuery.data?.items, sourcesQuery.data)
                  : "Select or create a collection to see real-time indexed file results."}
              </p>
            </div>
          </div>

          {selectedCollection ? (
            <>
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
                <p>Showing real-time active indexed files for the selected collection.</p>
                {collectionFilesQuery.data ? <span>{collectionFilesQuery.data.total} files</span> : null}
              </div>

              {collectionFilesQuery.isLoading ? <p>Loading collection results...</p> : null}

              {collectionFilesQuery.error instanceof Error ? (
                <div className="status-block page-card">
                  <strong>Collection results unavailable</strong>
                  <p>{collectionFilesQuery.error.message}</p>
                </div>
              ) : null}

              {collectionFilesQuery.data && collectionFilesQuery.data.items.length === 0 ? (
                <div className="future-frame">No active indexed files currently match this collection.</div>
              ) : null}

              {collectionFilesQuery.data && collectionFilesQuery.data.items.length > 0 ? (
                <>
                  <div className="files-list">
                    {collectionFilesQuery.data.items.map((item) => (
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
            </>
          ) : (
            <div className="future-frame">Select or create a collection to see reusable file retrieval results here.</div>
          )}
        </div>
      </div>
    </section>
  );
}
