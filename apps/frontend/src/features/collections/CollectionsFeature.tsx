import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
import type { CollectionVM, CreateCollectionInput, UpdateCollectionInput } from "../../entities/collection/types";
import type { ColorTagValue, FileListSortBy, FileListSortOrder, FileType } from "../../entities/file/types";
import {
  createCollection,
  deleteCollection,
  getCollectionStats,
  listCollectionFiles,
  listCollections,
  updateCollection,
} from "../../services/api/collectionsApi";
import { getSources } from "../../services/api/sourcesApi";
import { listTags } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";
import { invalidateCollectionSurfaces } from "../../services/query/invalidation";
import { ConfirmDialog } from "../../shared/ui/components";
import { CollectionForm } from "./CollectionForm";
import { CollectionList } from "./CollectionList";
import { CollectionResults } from "./CollectionResults";
import { buildCollectionNavLinks, getEntryNote } from "./collectionsHelpers";

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
  const [confirmDeleteCollectionId, setConfirmDeleteCollectionId] = useState<number | null>(null);

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

  const collectionStatsQuery = useQuery({
    queryKey: queryKeys.collectionStats(selectedCollectionId ?? 0),
    queryFn: () => getCollectionStats(selectedCollectionId as number),
    enabled: selectedCollectionId !== null && !(collectionsQuery.error instanceof Error),
  });

  const collectionFilesQuery = useQuery({
    queryKey: collectionFilesQueryParams ? queryKeys.collectionFiles(collectionFilesQueryParams) : ["collection-files", "idle"],
    queryFn: () => listCollectionFiles(collectionFilesQueryParams as NonNullable<typeof collectionFilesQueryParams>),
    enabled: selectedCollectionId !== null && !(collectionsQuery.error instanceof Error),
  });

  const createCollectionMutation = useMutation({
    mutationFn: (input: CreateCollectionInput) => createCollection(input),
    onSuccess: async (createdCollection) => {
      await invalidateCollectionSurfaces(queryClient);
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
      await invalidateCollectionSurfaces(queryClient);
      setSelectedCollectionId(updatedCollection.id);
      setPage(1);
    },
  });

  const deleteCollectionMutation = useMutation({
    mutationFn: (collectionId: number) => deleteCollection(collectionId),
    onSuccess: async (_, deletedCollectionId) => {
      await invalidateCollectionSurfaces(queryClient);

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
  const {
    mediaLink: mediaCompatibleCollection,
    booksLink: booksCompatibleCollection,
    softwareLink: softwareCompatibleCollection,
    gamesLink: gamesCompatibleCollection,
  } = useMemo(() => buildCollectionNavLinks(selectedCollection), [selectedCollection]);

  useEffect(() => {
    if (hasAppliedPrefillRef.current) return;

    const name = searchParams.get("prefill_name");
    const fileType = searchParams.get("prefill_file_type");
    const tagId = searchParams.get("prefill_tag_id");
    const colorTag = searchParams.get("prefill_color_tag");

    if (name !== null) setName(name);
    if (["image", "video", "document", "archive", "other"].includes(fileType ?? "")) setFileType(fileType as FileType);
    if (tagId !== null) setTagId(tagId);
    if (["red", "yellow", "green", "blue", "purple"].includes(colorTag ?? "")) setColorTag(colorTag as ColorTagValue);
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

  const handleCancelEdit = () => {
    setIsEditingSelected(false);
    setName("");
    setFileType("");
    setTagId("");
    setColorTag("");
    setSourceId("");
    setParentPath("");
  };

  return (
    <section className="feature-shell refind-surface refind-surface--collections">
      <div className="feature-header refind-surface__header">
        <span className="page-header__eyebrow">{t("features.collections.eyebrow")}</span>
        <h3>{t("features.collections.title")}</h3>
        <p>{t("features.collections.description")}</p>
      </div>

      <div className="collections-layout">
        <aside className="collections-sidebar">
          <CollectionForm
            isEditingSelected={isEditingSelected}
            entryNote={entryNote}
            name={name}
            fileType={fileType}
            tagId={tagId}
            colorTag={colorTag}
            sourceId={sourceId}
            parentPath={parentPath}
            tagsQuery={tagsQuery}
            sourcesQuery={sourcesQuery}
            colorTagOptions={colorTagOptions}
            fileTypeOptions={fileTypeOptions}
            canChooseTags={canChooseTags}
            canChooseSources={canChooseSources}
            formError={formError}
            isFormPending={isFormPending}
            onNameChange={setName}
            onFileTypeChange={setFileType}
            onTagIdChange={setTagId}
            onColorTagChange={setColorTag}
            onSourceIdChange={setSourceId}
            onParentPathChange={setParentPath}
            onSubmit={handleSubmit}
            onCancelEdit={handleCancelEdit}
          />

          <CollectionList
            collectionsQuery={collectionsQuery}
            selectedCollectionId={selectedCollectionId}
            tagsData={tagsQuery.data?.items}
            sourcesData={sourcesQuery.data}
            deleteCollectionPending={deleteCollectionMutation.isPending}
            onSelectCollection={(id) => {
              setSelectedCollectionId(id);
              setPage(1);
            }}
            onEditCollection={(collection) => {
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
            onDeleteCollection={(id) => setConfirmDeleteCollectionId(id)}
            onNavigateBrowse={() => navigate("/browse-v2")}
          />
        </aside>

        {confirmDeleteCollectionId !== null ? (
          <ConfirmDialog
            open={confirmDeleteCollectionId !== null}
            title={t("features.collections.deleteConfirmTitle")}
            message={t("features.collections.deleteConfirmMessage")}
            confirmLabel={t("common.actions.delete")}
            onConfirm={() => {
              deleteCollectionMutation.mutate(confirmDeleteCollectionId);
              setConfirmDeleteCollectionId(null);
            }}
            onCancel={() => setConfirmDeleteCollectionId(null)}
          />
        ) : null}

        <CollectionResults
          selectedCollection={selectedCollection}
          collectionStats={collectionStatsQuery.data?.item ?? null}
          collectionFilesQuery={collectionFilesQuery}
          page={page}
          totalPages={totalPages}
          sortBy={sortBy}
          sortOrder={sortOrder}
          selectedItemId={selectedItemId}
          tagsData={tagsQuery.data?.items}
          sourcesData={sourcesQuery.data}
          mediaLink={mediaCompatibleCollection}
          booksLink={booksCompatibleCollection}
          gamesLink={gamesCompatibleCollection}
          softwareLink={softwareCompatibleCollection}
          onPageChange={setPage}
          onSortByChange={(value) => {
            setSortBy(value);
            setPage(1);
          }}
          onSortOrderChange={(value) => {
            setSortOrder(value);
            setPage(1);
          }}
          onSelectItem={selectItem}
          onNavigate={navigate}
        />
      </div>
    </section>
  );
}
