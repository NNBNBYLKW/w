import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import type { CollectionVM, CreateCollectionInput, UpdateCollectionInput } from "../../entities/collection/types";
import type { ColorTagValue, FileListSortBy, FileListSortOrder, FileType } from "../../entities/file/types";
import type { SourceVM } from "../../entities/source/types";
import type { TagItemVM } from "../../entities/tag/types";
import {
  createCollection,
  deleteCollection,
  CollectionsApiError,
  listCollectionFiles,
  listCollections,
  updateCollection,
} from "../../services/api/collectionsApi";
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

function getEntryNote(entry: string | null): string | null {
  if (entry === "media") {
    return "Use this form to save the current media filters as a reusable collection.";
  }
  if (entry === "books") {
    return "Use this form to save the current book filters as a reusable collection.";
  }
  if (entry === "software") {
    return "Use this form to save the current software filters as a reusable collection.";
  }
  if (entry === "games") {
    return "Use this form to save the current game retrieval filters as a reusable collection.";
  }
  return null;
}

function applyCollectionFormValues(
  collection: Pick<CollectionVM, "name" | "file_type" | "tag_id" | "color_tag" | "source_id" | "parent_path">,
  setters: {
    setName: (value: string) => void;
    setFileType: (value: FileType | "") => void;
    setTagId: (value: string) => void;
    setColorTag: (value: ColorTagValue | "") => void;
    setSourceId: (value: string) => void;
    setParentPath: (value: string) => void;
  },
) {
  setters.setName(collection.name);
  setters.setFileType(collection.file_type ?? "");
  setters.setTagId(collection.tag_id === null ? "" : String(collection.tag_id));
  setters.setColorTag(collection.color_tag ?? "");
  setters.setSourceId(collection.source_id === null ? "" : String(collection.source_id));
  setters.setParentPath(collection.parent_path ?? "");
}


export function CollectionsFeature() {
  const queryClient = useQueryClient();
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const selectItem = useUIStore((state) => state.selectItem);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const hasAppliedPrefillRef = useRef(false);

  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [isEditingSelected, setIsEditingSelected] = useState(false);
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
  const entryNote = getEntryNote(searchParams.get("entry"));

  useEffect(() => {
    if (!isEditingSelected || !selectedCollection) {
      return;
    }

    applyCollectionFormValues(selectedCollection, {
      setName,
      setFileType,
      setTagId,
      setColorTag,
      setSourceId,
      setParentPath,
    });
  }, [isEditingSelected, selectedCollection]);

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
      setIsEditingSelected(false);
      setName("");
      setFileType("");
      setTagId("");
      setColorTag("");
      setSourceId("");
      setParentPath("");
    },
  });

  const updateCollectionMutation = useMutation({
    mutationFn: ({ collectionId, input }: { collectionId: number; input: UpdateCollectionInput }) =>
      updateCollection(collectionId, input),
    onSuccess: async (updatedCollection) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.collections });
      await queryClient.invalidateQueries({ queryKey: ["collection-files"] });
      setSelectedCollectionId(updatedCollection.id);
      setPage(1);
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
  const mediaCompatibleCollection = useMemo(() => {
    if (!selectedCollection) {
      return null;
    }

    if (selectedCollection.source_id !== null || selectedCollection.parent_path !== null) {
      return null;
    }

    if (
      selectedCollection.file_type !== null &&
      selectedCollection.file_type !== "image" &&
      selectedCollection.file_type !== "video"
    ) {
      return null;
    }

    const params = new URLSearchParams({
      entry: "collections",
    });

    if (selectedCollection.file_type === "image" || selectedCollection.file_type === "video") {
      params.set("view_scope", selectedCollection.file_type);
    }
    if (selectedCollection.tag_id !== null) {
      params.set("tag_id", String(selectedCollection.tag_id));
    }
    if (selectedCollection.color_tag !== null) {
      params.set("color_tag", selectedCollection.color_tag);
    }

    return `/library/media?${params.toString()}`;
  }, [selectedCollection]);
  const booksCompatibleCollection = useMemo(() => {
    if (!selectedCollection) {
      return null;
    }

    if (selectedCollection.source_id !== null || selectedCollection.parent_path !== null) {
      return null;
    }

    if (selectedCollection.file_type !== null && selectedCollection.file_type !== "document") {
      return null;
    }

    const params = new URLSearchParams({
      entry: "collections",
    });

    if (selectedCollection.tag_id !== null) {
      params.set("tag_id", String(selectedCollection.tag_id));
    }
    if (selectedCollection.color_tag !== null) {
      params.set("color_tag", selectedCollection.color_tag);
    }

    return `/library/books?${params.toString()}`;
  }, [selectedCollection]);
  const softwareCompatibleCollection = useMemo(() => {
    if (!selectedCollection) {
      return null;
    }

    if (
      selectedCollection.file_type !== null ||
      selectedCollection.source_id !== null ||
      selectedCollection.parent_path !== null
    ) {
      return null;
    }

    const params = new URLSearchParams({
      entry: "collections",
    });

    if (selectedCollection.tag_id !== null) {
      params.set("tag_id", String(selectedCollection.tag_id));
    }
    if (selectedCollection.color_tag !== null) {
      params.set("color_tag", selectedCollection.color_tag);
    }

    return `/library/software?${params.toString()}`;
  }, [selectedCollection]);
  const gamesCompatibleCollection = useMemo(() => {
    if (!selectedCollection) {
      return null;
    }

    if (
      selectedCollection.file_type !== null ||
      selectedCollection.source_id !== null ||
      selectedCollection.parent_path !== null
    ) {
      return null;
    }

    const params = new URLSearchParams({
      entry: "collections",
    });

    if (selectedCollection.tag_id !== null) {
      params.set("tag_id", String(selectedCollection.tag_id));
    }
    if (selectedCollection.color_tag !== null) {
      params.set("color_tag", selectedCollection.color_tag);
    }

    return `/library/games?${params.toString()}`;
  }, [selectedCollection]);

  useEffect(() => {
    if (hasAppliedPrefillRef.current) {
      return;
    }

    const prefillName = searchParams.get("prefill_name");
    const prefillFileType = searchParams.get("prefill_file_type");
    const prefillTagId = searchParams.get("prefill_tag_id");
    const prefillColorTag = searchParams.get("prefill_color_tag");

    if (prefillName !== null) {
      setName(prefillName);
    }
    if (
      prefillFileType === "image" ||
      prefillFileType === "video" ||
      prefillFileType === "document" ||
      prefillFileType === "archive" ||
      prefillFileType === "other"
    ) {
      setFileType(prefillFileType);
    }
    if (prefillTagId !== null) {
      setTagId(prefillTagId);
    }
    if (
      prefillColorTag === "red" ||
      prefillColorTag === "yellow" ||
      prefillColorTag === "green" ||
      prefillColorTag === "blue" ||
      prefillColorTag === "purple"
    ) {
      setColorTag(prefillColorTag);
    }

    hasAppliedPrefillRef.current = true;
  }, [searchParams]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isEditingSelected && selectedCollection) {
      const payload: UpdateCollectionInput = {
        name,
        file_type: fileType || null,
        tag_id: tagId ? Number(tagId) : null,
        color_tag: colorTag || null,
        source_id: sourceId ? Number(sourceId) : null,
        parent_path: parentPath.trim() ? parentPath.trim() : null,
      };
      updateCollectionMutation.mutate({
        collectionId: selectedCollection.id,
        input: payload,
      });
      return;
    }

    const payload: CreateCollectionInput = { name };
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
  const formError =
    createCollectionMutation.error instanceof Error
      ? createCollectionMutation.error.message
      : updateCollectionMutation.error instanceof Error
        ? updateCollectionMutation.error.message
        : null;
  const isFormPending = createCollectionMutation.isPending || updateCollectionMutation.isPending;

  return (
    <section className="feature-shell">
      <div className="feature-header">
        <span className="page-header__eyebrow">Saved retrieval surface</span>
        <h3>Reusable file retrieval</h3>
        <p>Save a narrow set of retrieval conditions here and keep using shared details as the single-item inspection center.</p>
      </div>

      <div className="collections-layout">
        <aside className="collections-sidebar">
          <form className="form-grid collections-form" onSubmit={handleSubmit}>
            <div className="collections-form__header">
              <span className="page-header__eyebrow">{isEditingSelected ? "Edit collection" : "Create collection"}</span>
              <p>
                {isEditingSelected
                  ? "Update the selected saved retrieval without turning Collections into a rules platform."
                  : "Store a minimal file retrieval condition set."}
              </p>
            </div>
            {entryNote ? <div className="context-flow-note">{entryNote}</div> : null}

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

            {formError ? <p className="collections-form__error">{formError}</p> : null}

            <div className="collections-form__actions">
              <button className="primary-button" type="submit" disabled={isFormPending}>
                {isFormPending ? "Saving..." : isEditingSelected ? "Update collection" : "Create collection"}
              </button>
              {isEditingSelected ? (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => {
                    setIsEditingSelected(false);
                    setName("");
                    setFileType("");
                    setTagId("");
                    setColorTag("");
                    setSourceId("");
                    setParentPath("");
                  }}
                >
                  Switch to create
                </button>
              ) : null}
            </div>
          </form>

          <div className="collections-list-shell">
            <div className="collections-list-shell__header">
              <span className="page-header__eyebrow">Collections</span>
              {collectionsQuery.data ? <p>{collectionsQuery.data.items.length} saved collections</p> : <p>Saved reusable entry points</p>}
            </div>

            {collectionsQuery.isLoading ? <p>Loading saved retrievals...</p> : null}

            {collectionsQuery.error instanceof Error ? (
              <div className="status-block page-card">
                <strong>Collections unavailable</strong>
                <p>{collectionsQuery.error.message}</p>
              </div>
            ) : null}

            {collectionsQuery.data && collectionsQuery.data.items.length === 0 ? (
              <div className="future-frame">No saved retrievals yet. Create one to reuse a narrow set of indexed-file conditions.</div>
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
                        <strong title={collection.name}>{collection.name}</strong>
                        <p title={buildCollectionSummary(collection, tagsQuery.data?.items, sourcesQuery.data)}>
                          {buildCollectionSummary(collection, tagsQuery.data?.items, sourcesQuery.data)}
                        </p>
                      </div>
                    </button>
                    <div className="collections-list__actions">
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => {
                          setSelectedCollectionId(collection.id);
                          setPage(1);
                          setIsEditingSelected(true);
                          applyCollectionFormValues(collection, {
                            setName,
                            setFileType,
                            setTagId,
                            setColorTag,
                            setSourceId,
                            setParentPath,
                          });
                        }}
                      >
                        Edit
                      </button>
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
            <div className="files-meta-row__actions">
              {mediaCompatibleCollection ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    navigate(mediaCompatibleCollection);
                  }}
                >
                  Open matching media
                </button>
              ) : null}
              {booksCompatibleCollection ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    navigate(booksCompatibleCollection);
                  }}
                >
                  Open matching books
                </button>
              ) : null}
              {gamesCompatibleCollection ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    navigate(gamesCompatibleCollection);
                  }}
                >
                  Open matching games
                </button>
              ) : null}
              {softwareCompatibleCollection ? (
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    navigate(softwareCompatibleCollection);
                  }}
                >
                  Open matching software
                </button>
              ) : null}
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

              {collectionFilesQuery.isLoading ? <p>Loading matching files...</p> : null}

              {collectionFilesQuery.error instanceof Error ? (
                <div className="status-block page-card">
                  <strong>Collection results unavailable</strong>
                  <p>{collectionFilesQuery.error.message}</p>
                </div>
              ) : null}

              {collectionFilesQuery.data && collectionFilesQuery.data.items.length === 0 ? (
                <div className="future-frame">No active indexed files currently match this saved retrieval.</div>
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
