import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
import type { CollectionVM, CreateCollectionInput, UpdateCollectionInput } from "../../entities/collection/types";
import type { ColorTagValue, FileListSortBy, FileListSortOrder, FileType } from "../../entities/file/types";
import type { SourceVM } from "../../entities/source/types";
import type { TagItemVM } from "../../entities/tag/types";
import {
  createCollection,
  deleteCollection,
  listCollectionFiles,
  listCollections,
  updateCollection,
} from "../../services/api/collectionsApi";
import { getSources } from "../../services/api/sourcesApi";
import { listTags } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";

function formatBytes(value: number | null): string {
  return value === null ? t("common.states.sizeUnavailable") : `${value.toLocaleString()} bytes`;
}

function getTagLabel(tagId: number | null, tags: TagItemVM[] | undefined): string | null {
  if (tagId === null) {
    return null;
  }
  const match = tags?.find((tag) => tag.id === tagId);
  return match?.name ?? t("common.labels.tagId", { id: tagId });
}

function getSourceLabel(sourceId: number | null, sources: SourceVM[] | undefined): string | null {
  if (sourceId === null) {
    return null;
  }

  const match = sources?.find((source) => source.id === sourceId);
  if (!match) {
    return `${t("common.labels.source")} #${sourceId}`;
  }

  return match.display_name?.trim() || match.path;
}

function getFileTypeLabel(fileType: FileType): string {
  if (fileType === "image") {
    return t("common.fileTypes.image");
  }
  if (fileType === "video") {
    return t("common.fileTypes.video");
  }
  if (fileType === "document") {
    return t("common.fileTypes.document");
  }
  if (fileType === "archive") {
    return t("common.fileTypes.archive");
  }
  return t("common.fileTypes.other");
}

function getColorTagLabel(colorTag: ColorTagValue): string {
  if (colorTag === "red") {
    return t("common.colors.red");
  }
  if (colorTag === "yellow") {
    return t("common.colors.yellow");
  }
  if (colorTag === "green") {
    return t("common.colors.green");
  }
  if (colorTag === "blue") {
    return t("common.colors.blue");
  }
  return t("common.colors.purple");
}

function buildCollectionSummary(collection: CollectionVM, tags: TagItemVM[] | undefined, sources: SourceVM[] | undefined): string {
  const parts: string[] = [];

  if (collection.file_type) {
    parts.push(t("features.collections.summary.type", { value: getFileTypeLabel(collection.file_type) }));
  }

  const tagLabel = getTagLabel(collection.tag_id, tags);
  if (tagLabel) {
    parts.push(t("features.collections.summary.tag", { value: tagLabel }));
  }

  if (collection.color_tag) {
    parts.push(t("features.collections.summary.color", { value: getColorTagLabel(collection.color_tag) }));
  }

  const sourceLabel = getSourceLabel(collection.source_id, sources);
  if (sourceLabel) {
    parts.push(t("features.collections.summary.source", { value: sourceLabel }));
  }

  if (collection.parent_path) {
    parts.push(t("features.collections.summary.path", { value: collection.parent_path }));
  }

  return parts.length > 0 ? parts.join(" | ") : t("features.collections.summary.all");
}

function getEntryNote(entry: string | null): string | null {
  if (entry === "media") {
    return t("features.collections.saveFrom.media");
  }
  if (entry === "books") {
    return t("features.collections.saveFrom.books");
  }
  if (entry === "software") {
    return t("features.collections.saveFrom.software");
  }
  if (entry === "games") {
    return t("features.collections.saveFrom.games");
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
  const colorTagOptions: Array<{ label: string; value: ColorTagValue }> = [
    { label: t("common.colors.red"), value: "red" },
    { label: t("common.colors.yellow"), value: "yellow" },
    { label: t("common.colors.green"), value: "green" },
    { label: t("common.colors.blue"), value: "blue" },
    { label: t("common.colors.purple"), value: "purple" },
  ];
  const fileTypeOptions: Array<{ label: string; value: FileType }> = [
    { label: t("common.fileTypes.image"), value: "image" },
    { label: t("common.fileTypes.video"), value: "video" },
    { label: t("common.fileTypes.document"), value: "document" },
    { label: t("common.fileTypes.archive"), value: "archive" },
    { label: t("common.fileTypes.other"), value: "other" },
  ];

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

    return `/software?${params.toString()}`;
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
        <span className="page-header__eyebrow">{t("features.collections.eyebrow")}</span>
        <h3>{t("features.collections.title")}</h3>
        <p>{t("features.collections.description")}</p>
      </div>

      <div className="collections-layout">
        <aside className="collections-sidebar">
          <form className="form-grid collections-form" onSubmit={handleSubmit}>
            <div className="collections-form__header">
              <span className="page-header__eyebrow">
                {isEditingSelected ? t("features.collections.editCollection") : t("features.collections.createCollection")}
              </span>
              <p>
                {isEditingSelected
                  ? t("features.collections.editDescription")
                  : t("features.collections.createDescription")}
              </p>
            </div>
            {entryNote ? <div className="context-flow-note">{entryNote}</div> : null}

            <label className="field-stack">
              <span>{t("features.collections.name")}</span>
              <input
                className="text-input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder={t("features.collections.namePlaceholder")}
              />
            </label>

            <label className="field-stack">
              <span>{t("common.labels.fileType")}</span>
              <select className="select-input" value={fileType} onChange={(event) => setFileType(event.target.value as FileType | "")}>
                <option value="">{t("features.collections.anyType")}</option>
                {fileTypeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field-stack">
              <span>{t("common.labels.tag")}</span>
              <select
                className="select-input"
                value={tagId}
                onChange={(event) => setTagId(event.target.value)}
                disabled={tagsQuery.isLoading || !canChooseTags}
              >
                <option value="">{t("features.collections.anyTag")}</option>
                {tagsQuery.data?.items.map((tag) => (
                  <option key={tag.id} value={String(tag.id)}>
                    {tag.name}
                  </option>
                ))}
              </select>
            </label>

            {tagsQuery.error instanceof Error ? (
              <p className="collections-form__note">{t("features.collections.tagsUnavailableNote")}</p>
            ) : null}

            <label className="field-stack">
              <span>{t("common.labels.color")}</span>
              <select
                className="select-input"
                value={colorTag}
                onChange={(event) => setColorTag(event.target.value as ColorTagValue | "")}
              >
                <option value="">{t("common.colors.any")}</option>
                {colorTagOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field-stack">
              <span>{t("common.labels.source")}</span>
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
                <option value="">{t("features.collections.anySource")}</option>
                {sourcesQuery.data?.map((source) => (
                  <option key={source.id} value={String(source.id)}>
                    {source.display_name?.trim() || source.path}
                  </option>
                ))}
              </select>
            </label>

            {sourcesQuery.error instanceof Error ? (
              <p className="collections-form__note">{t("features.collections.sourcesUnavailableNote")}</p>
            ) : null}

            <label className="field-stack">
              <span>{t("common.labels.parentPath")}</span>
              <input
                className="text-input"
                value={parentPath}
                onChange={(event) => setParentPath(event.target.value)}
                placeholder={t("features.collections.parentPathPlaceholder")}
                disabled={!sourceId}
              />
            </label>

            {formError ? <p className="collections-form__error">{formError}</p> : null}

            <div className="collections-form__actions">
              <button className="primary-button" type="submit" disabled={isFormPending}>
                {isFormPending
                  ? t("common.actions.saving")
                  : isEditingSelected
                    ? t("common.actions.updateCollection")
                    : t("common.actions.createCollection")}
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
                  {t("common.actions.switchToCreate")}
                </button>
              ) : null}
            </div>
          </form>

          <div className="collections-list-shell">
            <div className="collections-list-shell__header">
              <span className="page-header__eyebrow">{t("features.collections.listEyebrow")}</span>
              {collectionsQuery.data ? (
                <p>{t("common.labels.collections", { count: collectionsQuery.data.items.length })}</p>
              ) : (
                <p>{t("features.collections.listFallback")}</p>
              )}
            </div>

            {collectionsQuery.isLoading ? <p>{t("features.collections.listLoading")}</p> : null}

            {collectionsQuery.error instanceof Error ? (
              <div className="status-block page-card">
                <strong>{t("features.collections.listUnavailableTitle")}</strong>
                <p>{collectionsQuery.error.message}</p>
              </div>
            ) : null}

            {collectionsQuery.data && collectionsQuery.data.items.length === 0 ? (
              <div className="future-frame">{t("features.collections.listEmpty")}</div>
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
                        {t("common.actions.edit")}
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => {
                          deleteCollectionMutation.mutate(collection.id);
                        }}
                        disabled={deleteCollectionMutation.isPending}
                      >
                        {t("common.actions.delete")}
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
              <span className="page-header__eyebrow">{t("features.collections.resultsEyebrow")}</span>
              <h3>{selectedCollection?.name ?? t("features.collections.chooseCollection")}</h3>
              <p>
                {selectedCollection
                  ? buildCollectionSummary(selectedCollection, tagsQuery.data?.items, sourcesQuery.data)
                  : t("features.collections.chooseCollectionDescription")}
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
                  {t("common.actions.openMatchingMedia")}
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
                  {t("common.actions.openMatchingBooks")}
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
                  {t("common.actions.openMatchingGames")}
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
                  {t("common.actions.openMatchingSoftware")}
                </button>
              ) : null}
            </div>
          </div>

          {selectedCollection ? (
            <>
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
                <p>{t("features.collections.resultsMeta")}</p>
                {collectionFilesQuery.data ? <span>{t("common.labels.files", { count: collectionFilesQuery.data.total })}</span> : null}
              </div>

              {collectionFilesQuery.isLoading ? <p>{t("features.collections.resultsLoading")}</p> : null}

              {collectionFilesQuery.error instanceof Error ? (
                <div className="status-block page-card">
                  <strong>{t("features.collections.resultsUnavailableTitle")}</strong>
                  <p>{collectionFilesQuery.error.message}</p>
                </div>
              ) : null}

              {collectionFilesQuery.data && collectionFilesQuery.data.items.length === 0 ? (
                <div className="future-frame">{t("features.collections.resultsEmpty")}</div>
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
            </>
          ) : (
            <div className="future-frame">{t("features.collections.emptyFallback")}</div>
          )}
        </div>
      </div>
    </section>
  );
}
