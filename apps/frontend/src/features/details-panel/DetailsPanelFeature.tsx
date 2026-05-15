import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useUIStore } from "../../app/providers/uiStore";
import { t, useLocale } from "../../shared/text";
import { EmptyState, InspectorSection, LoadingState } from "../../shared/ui/components";
import { DetailsIdentitySection } from "./sections/DetailsIdentitySection";
import { DetailsPlacementSection } from "./sections/DetailsPlacementSection";
import { DetailsRatingSection } from "./sections/DetailsRatingSection";
import { DetailsGameStatusSection } from "./sections/DetailsGameStatusSection";
import { DetailsColorTagSection } from "./sections/DetailsColorTagSection";
import { DetailsTagsSection } from "./sections/DetailsTagsSection";
import { DetailsActionsSection } from "./sections/DetailsActionsSection";
import { DetailsFactListSection } from "./sections/DetailsFactListSection";
import { DetailsMetadataSection } from "./sections/DetailsMetadataSection";
import { DetailsStorageSection } from "./sections/DetailsStorageSection";
import { DetailsPreviewSection } from "./sections/DetailsPreviewSection";
import { DetailsBookInfoSection } from "./sections/DetailsBookInfoSection";
import { DetailsSoftwareInfoSection } from "./sections/DetailsSoftwareInfoSection";
import { DetailsMediaRetrievalSection } from "./sections/DetailsMediaRetrievalSection";
import { DetailsBookRetrievalSection } from "./sections/DetailsBookRetrievalSection";
import { DetailsSoftwareRetrievalSection } from "./sections/DetailsSoftwareRetrievalSection";
import { DetailsGameRetrievalSection } from "./sections/DetailsGameRetrievalSection";
import { useRetryingThumbnail, useThumbnailWarmup } from "../../shared/ui/thumbnail";
import type {
  ColorTagValue,
  FileDetailResponseVM,
  FileRatingValue,
  FileStatusValue,
  ManualPlacementValue,
} from "../../entities/file/types";
import { updateFileColorTag } from "../../services/api/colorTagsApi";
import {
  getFileThumbnailUrl,
  getFileVideoPreview,
  getFileVideoPreviewFrameUrl,
} from "../../services/api/fileDetailsApi";
import {
  hasDesktopOpenActionsBridge,
  normalizeIndexedFilePath,
  openIndexedContainingFolder,
  openIndexedFile,
} from "../../services/desktop/openActions";
import { getFileDetails } from "../../services/api/fileDetailsApi";
import { queryKeys } from "../../services/query/queryKeys";
import { invalidateDetailsPanelFileDetail, invalidateFileOrganizationSurfaces } from "../../services/query/invalidation";
import { updateFileStatus } from "../../services/api/statusApi";
import { attachTagToFile, removeTagFromFile } from "../../services/api/tagsApi";
import { updateFilePlacement, updateFileUserMeta } from "../../services/api/userMetaApi";
import {
  COLOR_TAG_OPTIONS,
  GAME_STATUS_OPTIONS,
  PLACEMENT_OPTIONS,
  formatFavoriteLabel,
  formatPlacementLabel,
  formatRatingLabel,
  formatStatusLabel,
  inferBookFormat,
  inferGameEntry,
  inferSoftwareFormat,
} from "./shared/detailsHelpers";


export function DetailsPanelFeature() {
  useLocale();
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const batchSelectionSummary = useUIStore((state) => state.batchSelectionSummary);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const [tagInput, setTagInput] = useState("");
  const [tagMutationError, setTagMutationError] = useState<string | null>(null);
  const [colorTagMutationError, setColorTagMutationError] = useState<string | null>(null);
  const [statusMutationError, setStatusMutationError] = useState<string | null>(null);
  const [userMetaMutationError, setUserMetaMutationError] = useState<string | null>(null);
  const [placementMutationError, setPlacementMutationError] = useState<string | null>(null);
  const [openActionError, setOpenActionError] = useState<string | null>(null);
  const [pendingOpenAction, setPendingOpenAction] = useState<"file" | "folder" | null>(null);
  const [previewLoadFailed, setPreviewLoadFailed] = useState(false);
  const [singlePreviewLoaded, setSinglePreviewLoaded] = useState(false);
  const [videoPreviewFrameIndex, setVideoPreviewFrameIndex] = useState(0);
  const [videoPreviewPlaybackFailed, setVideoPreviewPlaybackFailed] = useState(false);
  const [retrievalHint, setRetrievalHint] = useState<
    | { kind: "tag"; message: string }
    | { kind: "color"; message: string }
    | { kind: "status"; message: string }
    | { kind: "placement"; message: string }
    | null
  >(null);
  const parsedFileId = selectedItemId !== null ? Number(selectedItemId) : null;
  const hasInvalidSelectedId =
    selectedItemId !== null && (!Number.isInteger(parsedFileId) || parsedFileId === null || parsedFileId <= 0);
  const hasDesktopOpenActions = hasDesktopOpenActionsBridge();
  const isGamesRoute = location.pathname.startsWith("/library/games");
  const isBooksRoute = location.pathname.startsWith("/books") || location.pathname.startsWith("/library/books");
  const isSoftwareRoute = location.pathname.startsWith("/software");

  useEffect(() => {
    setPreviewLoadFailed(false);
    setSinglePreviewLoaded(false);
    setVideoPreviewFrameIndex(0);
    setVideoPreviewPlaybackFailed(false);
  }, [selectedItemId]);


  const detailQuery = useQuery({
    queryKey: parsedFileId !== null ? queryKeys.fileDetail(parsedFileId) : ["file-detail", "idle"],
    queryFn: () => getFileDetails(parsedFileId as number),
    enabled: parsedFileId !== null && !hasInvalidSelectedId,
  });
  const currentItem = detailQuery.data?.item;
  const currentInferredBookFormat =
    currentItem !== undefined ? inferBookFormat(currentItem.name, currentItem.path) : null;
  const currentInferredSoftwareFormat =
    currentItem !== undefined ? inferSoftwareFormat(currentItem.name, currentItem.path) : null;
  const currentInferredGameEntry =
    currentItem !== undefined ? inferGameEntry(currentItem.name, currentItem.path) : false;
  const isBookContextForMutations = isBooksRoute || currentInferredBookFormat !== null;
  const isGameContextForMutations = isGamesRoute || currentInferredGameEntry || (currentItem?.status ?? null) !== null;
  const isSoftwareContextForMutations =
    !isGameContextForMutations && (isSoftwareRoute || currentInferredSoftwareFormat !== null);

  const videoPreviewQuery = useQuery({
    queryKey: parsedFileId !== null ? ["file-video-preview", parsedFileId] : ["file-video-preview", "idle"],
    queryFn: () => getFileVideoPreview(parsedFileId as number),
    enabled:
      parsedFileId !== null &&
      !hasInvalidSelectedId &&
      currentItem?.file_type === "video" &&
      singlePreviewLoaded &&
      !previewLoadFailed &&
      !videoPreviewPlaybackFailed,
    retry: false,
  });

  const videoPreviewFrameIndexes = videoPreviewQuery.data?.item.frame_indexes ?? [];
  const isVideoPreviewActive =
    currentItem?.file_type === "video" &&
    !videoPreviewPlaybackFailed &&
    videoPreviewFrameIndexes.length === 6;
  const detailThumbnailWarmup = useThumbnailWarmup(currentItem ? [currentItem.id] : []);
  const previewThumbnail = useRetryingThumbnail<HTMLDivElement>({
    enabled: currentItem !== undefined && !isVideoPreviewActive && !detailThumbnailWarmup.isThumbnailDisabled(currentItem.id),
    onLoad: currentItem !== undefined ? () => detailThumbnailWarmup.markLoaded(currentItem.id) : undefined,
    refreshToken: currentItem !== undefined ? detailThumbnailWarmup.getRefreshToken(currentItem.id) : 0,
    thumbnailUrl: currentItem !== undefined ? getFileThumbnailUrl(currentItem.id) : undefined,
  });

  useEffect(() => {
    if (!isVideoPreviewActive) {
      setVideoPreviewFrameIndex(0);
      return;
    }

    const intervalId = window.setInterval(() => {
      setVideoPreviewFrameIndex((current) => (current + 1) % videoPreviewFrameIndexes.length);
    }, 800);

    return () => window.clearInterval(intervalId);
  }, [isVideoPreviewActive, videoPreviewFrameIndexes.length]);

  const addTagMutation = useMutation({
    mutationFn: (name: string) => attachTagToFile(parsedFileId as number, name),
    onMutate: () => setTagMutationError(null),
    onSuccess: async () => {
      setTagInput("");
      await invalidateDetailsPanelFileDetail(queryClient, parsedFileId as number);
      await invalidateFileOrganizationSurfaces(queryClient);
      setRetrievalHint({
        kind: "tag",
        message: isGameContextForMutations
          ? "Tags updated. Use Tags or Games to re-find this game entry naturally."
          : isSoftwareContextForMutations
            ? "Tags updated. Use Tags or Software to re-find this software-related file naturally."
            : "Tags updated. You can use Tags to re-find this file naturally.",
      });
    },
    onError: (error) => {
      setTagMutationError(error instanceof Error ? error.message : t("details.errors.addTagFailed"));
    },
  });

  const removeTagMutation = useMutation({
    mutationFn: (tagId: number) => removeTagFromFile(parsedFileId as number, tagId),
    onMutate: () => setTagMutationError(null),
    onSuccess: async () => {
      await invalidateDetailsPanelFileDetail(queryClient, parsedFileId as number);
      await invalidateFileOrganizationSurfaces(queryClient);
      setRetrievalHint({
        kind: "tag",
        message: isGameContextForMutations
          ? "Tags updated. Use Tags or Games to re-find this game entry naturally."
          : isSoftwareContextForMutations
            ? "Tags updated. Use Tags or Software to re-find this software-related file naturally."
            : "Tags updated. You can use Tags to re-find this file naturally.",
      });
    },
    onError: (error) => {
      setTagMutationError(error instanceof Error ? error.message : t("details.errors.removeTagFailed"));
    },
  });

  const colorTagMutation = useMutation({
    mutationFn: (colorTag: ColorTagValue | null) => updateFileColorTag(parsedFileId as number, colorTag),
    onMutate: () => setColorTagMutationError(null),
    onSuccess: (response) => {
      queryClient.setQueryData<FileDetailResponseVM | undefined>(
        queryKeys.fileDetail(parsedFileId as number),
        (current) => {
          if (!current || current.item.id !== response.item.id) {
            return current;
          }
          return {
            item: {
              ...current.item,
              color_tag: response.item.color_tag,
            },
          };
        },
      );
      void invalidateFileOrganizationSurfaces(queryClient);
      setRetrievalHint({
        kind: "color",
        message: response.item.color_tag
          ? isGameContextForMutations
            ? "Color tag updated. You can jump back into Games with the new color filter."
            : isBookContextForMutations
              ? "Color tag updated. You can jump back into Books with the new color filter."
              : isSoftwareContextForMutations
                ? "Color tag updated. You can jump back into Software with the new color filter."
                : "Color tag updated. You can jump back into Media with the new color filter."
          : isGameContextForMutations
            ? "Color tag cleared. Games, Recent, Tags, and Collections will refresh on the shared retrieval chain."
            : isBookContextForMutations
              ? "Color tag cleared. Books, Recent, Tags, and Collections will refresh on the shared retrieval chain."
              : isSoftwareContextForMutations
                ? "Color tag cleared. Software, Recent, Tags, and Collections will refresh on the shared retrieval chain."
                : "Color tag cleared. Media, Recent, Tags, and Collections will refresh on the shared retrieval chain.",
      });
    },
    onError: (error) => {
      setColorTagMutationError(error instanceof Error ? error.message : t("details.errors.updateColorTagFailed"));
    },
  });

  const statusMutation = useMutation({
    mutationFn: (status: FileStatusValue | null) => updateFileStatus(parsedFileId as number, status),
    onMutate: () => setStatusMutationError(null),
    onSuccess: (response) => {
      queryClient.setQueryData<FileDetailResponseVM | undefined>(
        queryKeys.fileDetail(parsedFileId as number),
        (current) => {
          if (!current || current.item.id !== response.item.id) {
            return current;
          }
          return {
            item: {
              ...current.item,
              status: response.item.status,
            },
          };
        },
      );
      void queryClient.invalidateQueries({ queryKey: ["games-list"] });
      setRetrievalHint({
        kind: "status",
        message: response.item.status
          ? `Game status updated to ${formatStatusLabel(response.item.status)}. You can jump back into Games with the same status filter.`
          : "Game status cleared. Games results will refresh on the current subset surface.",
      });
    },
    onError: (error) => {
      setStatusMutationError(error instanceof Error ? error.message : t("details.errors.updateStatusFailed"));
    },
  });

  const userMetaMutation = useMutation({
    mutationFn: (payload: { is_favorite?: boolean; rating?: FileRatingValue | null }) =>
      updateFileUserMeta(parsedFileId as number, payload),
    onMutate: () => setUserMetaMutationError(null),
    onSuccess: (response) => {
      queryClient.setQueryData<FileDetailResponseVM | undefined>(
        queryKeys.fileDetail(parsedFileId as number),
        (current) => {
          if (!current || current.item.id !== response.item.id) {
            return current;
          }
          return {
            item: {
              ...current.item,
              is_favorite: response.item.is_favorite,
              rating: response.item.rating,
            },
          };
        },
      );
      void invalidateFileOrganizationSurfaces(queryClient);
    },
    onError: (error) => {
      setUserMetaMutationError(error instanceof Error ? error.message : t("details.errors.updateUserMetaFailed"));
    },
  });

  const placementMutation = useMutation({
    mutationFn: (manualPlacement: ManualPlacementValue | null) => updateFilePlacement(parsedFileId as number, manualPlacement),
    onMutate: () => setPlacementMutationError(null),
    onSuccess: (response) => {
      queryClient.setQueryData<FileDetailResponseVM | undefined>(
        queryKeys.fileDetail(parsedFileId as number),
        (current) => {
          if (!current || current.item.id !== response.item.id) {
            return current;
          }
          return {
            item: {
              ...current.item,
              file_kind: response.item.file_kind,
              auto_placement: response.item.auto_placement,
              manual_placement: response.item.manual_placement,
              effective_placement: response.item.effective_placement,
            },
          };
        },
      );
      void invalidateFileOrganizationSurfaces(queryClient);
      setRetrievalHint({
        kind: "placement",
        message: t("details.placement.updatedHint"),
      });
    },
    onError: (error) => {
      setPlacementMutationError(error instanceof Error ? error.message : t("details.errors.updatePlacementFailed"));
    },
  });

  useEffect(() => {
    setTagInput("");
    setTagMutationError(null);
    setColorTagMutationError(null);
    setStatusMutationError(null);
    setUserMetaMutationError(null);
    setPlacementMutationError(null);
    setOpenActionError(null);
    setPendingOpenAction(null);
    setPreviewLoadFailed(false);
    setSinglePreviewLoaded(false);
    setVideoPreviewFrameIndex(0);
    setVideoPreviewPlaybackFailed(false);
    setRetrievalHint(null);
  }, [selectedItemId]);

  const handleOpenAction = async (action: "file" | "folder", filePath: string | null | undefined) => {
    const normalizedPath = normalizeIndexedFilePath(filePath);
    if (!normalizedPath) {
      setOpenActionError(t("details.errors.openActionNoPath"));
      return;
    }

    setOpenActionError(null);
    setPendingOpenAction(action);

    try {
      const result =
        action === "file"
          ? await openIndexedFile(normalizedPath)
          : await openIndexedContainingFolder(normalizedPath);

      if (!result.ok) {
        setOpenActionError(result.reason);
      }
    } catch (error) {
      setOpenActionError(error instanceof Error ? error.message : t("details.errors.openActionFailed"));
    } finally {
      setPendingOpenAction(null);
    }
  };

  let content: JSX.Element;

  if (batchSelectionSummary) {
    content = (
      <div className="details-panel details-inspector details-panel--batch">
        <InspectorSection>
          <span className="placeholder-pill">{t("details.placeholders.batch.eyebrow")}</span>
          <h3>{batchSelectionSummary.pageLabel}</h3>
          <p>{t("details.placeholders.batch.selectedCount", { count: batchSelectionSummary.selectedCount })}</p>
          <p>{t("details.placeholders.batch.description")}</p>
        </InspectorSection>
      </div>
    );
  } else if (selectedItemId === null) {
    content = (
      <div className="details-panel details-inspector details-panel--state">
        <EmptyState
          title={t("details.placeholders.awaitingSelection.title")}
          description={t("details.placeholders.awaitingSelection.description")}
        />
      </div>
    );
  } else if (hasInvalidSelectedId) {
    content = (
      <div className="details-panel details-inspector details-panel--state">
        <EmptyState
          title={t("details.placeholders.selectionError.title")}
          description={t("details.placeholders.selectionError.description")}
        />
      </div>
    );
  } else if (detailQuery.isLoading) {
    content = (
      <div className="details-panel details-inspector details-panel--state">
        <LoadingState message={t("details.placeholders.loading.description")} />
      </div>
    );
  } else if (detailQuery.error instanceof Error) {
    content = (
      <div className="details-panel details-inspector details-panel--state">
        <EmptyState
          title={t("details.placeholders.error.title")}
          description={detailQuery.error.message}
        />
      </div>
    );
  } else if (detailQuery.data) {
    const { item } = detailQuery.data;
    const isTagMutationPending = addTagMutation.isPending || removeTagMutation.isPending;
    const isColorTagMutationPending = colorTagMutation.isPending;
    const isStatusMutationPending = statusMutation.isPending;
    const isUserMetaMutationPending = userMetaMutation.isPending;
    const isPlacementMutationPending = placementMutation.isPending;
    const isOpenActionPending = pendingOpenAction !== null;
    const isImageFile = item.file_type === "image";
    const isVideoFile = item.file_type === "video";
    const isMediaFile = isImageFile || isVideoFile;
    const inferredBookFormat = inferBookFormat(item.name, item.path);
    const inferredSoftwareFormat = inferSoftwareFormat(item.name, item.path);
    const inferredGameEntry = inferGameEntry(item.name, item.path);
    const isBookContext = isBooksRoute || inferredBookFormat !== null;
    const isGameContext = isGamesRoute || inferredGameEntry || item.status !== null;
    const isSoftwareContext = !isGameContext && (isSoftwareRoute || inferredSoftwareFormat !== null);
    const isExeSoftwareFile = isSoftwareContext && inferredSoftwareFormat === "exe";
    const isPdfBookFile = isBookContext && inferredBookFormat === "pdf";
    const metadata = item.metadata;
    const firstTag = item.tags[0] ?? null;
    const activeVideoPreviewFrameIndex = videoPreviewFrameIndexes[videoPreviewFrameIndex] ?? videoPreviewFrameIndexes[0];
    const previewImageSrc =
      isVideoPreviewActive && activeVideoPreviewFrameIndex !== undefined
        ? getFileVideoPreviewFrameUrl(item.id, activeVideoPreviewFrameIndex)
        : previewThumbnail.imageSrc;
    content = (
      <div className="details-panel details-inspector details-panel--file">
        <div className="details-inspector__group details-inspector__group--identity">
          <DetailsIdentitySection name={item.name} fileType={item.file_type} id={item.id} />
          <DetailsFactListSection
            path={item.path}
            fileType={item.file_type}
            sizeBytes={item.size_bytes}
            id={item.id}
            sourceId={item.source_id}
            modifiedAtFs={item.modified_at_fs}
            createdAtFs={item.created_at_fs}
            discoveredAt={item.discovered_at}
            lastSeenAt={item.last_seen_at}
            isDeleted={item.is_deleted}
          />
        </div>
        {item.storage_state && (
          <div className="details-inspector__group details-inspector__group--storage">
            <InspectorSection title={t("details.storage.title")}>
              <DetailsStorageSection
                storageState={item.storage_state}
                path={item.path}
                originalPath={item.original_path}
                managedRootId={item.managed_root_id}
                managedAt={item.managed_at}
                inboxItemId={item.inbox_item_id}
              />
            </InspectorSection>
          </div>
        )}
        <div className="details-inspector__group details-inspector__group--organization">
          <DetailsPlacementSection
            manualPlacement={item.manual_placement}
            fileKind={item.file_kind}
            autoPlacementLabel={formatPlacementLabel(item.auto_placement)}
            effectivePlacementLabel={formatPlacementLabel(item.effective_placement)}
            isPending={isPlacementMutationPending}
            error={placementMutationError}
            placementOptions={PLACEMENT_OPTIONS}
            onChange={(value) => placementMutation.mutate(value === "auto" ? null : (value as ManualPlacementValue))}
          />
        {isBookContext && inferredBookFormat ? (
          <DetailsBookInfoSection
            name={item.name}
            format={inferredBookFormat}
            pageCount={metadata?.page_count ?? null}
          />
        ) : null}
        {isSoftwareContext && inferredSoftwareFormat ? (
          <DetailsSoftwareInfoSection
            name={item.name}
            format={inferredSoftwareFormat}
          />
        ) : null}
          <DetailsMetadataSection
            isMediaFile={isMediaFile}
            isVideoFile={isVideoFile}
            isBookContext={isBookContext}
            metadata={
              metadata
                ? {
                    width: metadata.width ?? null,
                    height: metadata.height ?? null,
                    duration_ms: metadata.duration_ms ?? null,
                    page_count: metadata.page_count ?? null,
                  }
                : null
            }
          />
        </div>
        {isImageFile || isVideoFile || isExeSoftwareFile || isPdfBookFile ? (
          <div className="details-inspector__group details-inspector__group--preview">
            <DetailsPreviewSection
              isImageFile={isImageFile}
              isVideoFile={isVideoFile}
              isExeSoftwareFile={isExeSoftwareFile}
              isPdfBookFile={isPdfBookFile}
              isVideoPreviewActive={isVideoPreviewActive}
              previewLoadFailed={previewLoadFailed}
              previewImageSrc={previewImageSrc}
              name={item.name}
              previewRef={previewThumbnail.ref}
              onImageError={() => {
                if (isVideoPreviewActive) {
                  setVideoPreviewPlaybackFailed(true);
                  return;
                }
                previewThumbnail.onError();
              }}
              onImageLoad={() => {
                if (!isVideoPreviewActive) {
                  setSinglePreviewLoaded(true);
                  previewThumbnail.onLoad();
                }
              }}
            />
          </div>
        ) : null}
        <div className="details-inspector__group details-inspector__group--signals">
          <DetailsRatingSection
            isFavorite={item.is_favorite}
            rating={item.rating}
            isPending={isUserMetaMutationPending}
            error={userMetaMutationError}
            favoriteLabel={formatFavoriteLabel(item.is_favorite)}
            ratingLabel={formatRatingLabel(item.rating)}
            onToggleFavorite={() => userMetaMutation.mutate({ is_favorite: !item.is_favorite })}
            onSetRating={(value) => userMetaMutation.mutate({ rating: value })}
            onClearRating={() => userMetaMutation.mutate({ rating: null })}
          />
          {isGameContext ? (
            <DetailsGameStatusSection
              status={item.status}
              isPending={isStatusMutationPending}
              error={statusMutationError}
              statusLabel={item.status ? formatStatusLabel(item.status) : t("details.values.none")}
              statusOptions={GAME_STATUS_OPTIONS}
              onChange={(value) => statusMutation.mutate(value)}
            />
          ) : null}
          <DetailsColorTagSection
            colorTag={item.color_tag}
            isPending={isColorTagMutationPending}
            error={colorTagMutationError}
            colorOptions={COLOR_TAG_OPTIONS}
            currentColorLabel={item.color_tag ?? t("details.values.none")}
            onChange={(value) => colorTagMutation.mutate(value)}
          />
          <DetailsTagsSection
            tags={item.tags}
            tagInput={tagInput}
            isPending={isTagMutationPending}
            error={tagMutationError}
            onTagInputChange={setTagInput}
            onAddTag={(event) => {
              event.preventDefault();
              addTagMutation.mutate(tagInput);
            }}
            onRemoveTag={(tagId) => removeTagMutation.mutate(tagId)}
          />
        </div>
        {isMediaFile && (firstTag || item.color_tag || (retrievalHint !== null && retrievalHint.kind !== "status")) ? (
          <DetailsMediaRetrievalSection
            fileId={item.id}
            firstTag={firstTag}
            colorTag={item.color_tag}
            retrievalMessage={retrievalHint?.message ?? null}
          />
        ) : null}
        {isBookContext && (firstTag || item.color_tag || retrievalHint?.kind === "tag" || retrievalHint?.kind === "color") ? (
          <DetailsBookRetrievalSection
            fileId={item.id}
            firstTag={firstTag}
            colorTag={item.color_tag}
            retrievalHintKind={retrievalHint?.kind ?? null}
            retrievalHintMessage={retrievalHint?.message ?? null}
          />
        ) : null}
        {isSoftwareContextForMutations &&
        (firstTag || item.color_tag || retrievalHint?.kind === "tag" || retrievalHint?.kind === "color") ? (
          <DetailsSoftwareRetrievalSection
            fileId={item.id}
            firstTag={firstTag}
            colorTag={item.color_tag}
            retrievalHintKind={retrievalHint?.kind ?? null}
            retrievalHintMessage={retrievalHint?.message ?? null}
          />
        ) : null}
        {isGameContext ? (
          <DetailsGameRetrievalSection
            fileId={item.id}
            firstTag={firstTag}
            colorTag={item.color_tag}
            status={item.status}
            retrievalHintKind={retrievalHint?.kind ?? null}
            retrievalHintMessage={retrievalHint?.message ?? null}
          />
        ) : null}
        <div className="details-inspector__group details-inspector__group--actions">
          <DetailsActionsSection
            isOpenActionPending={isOpenActionPending}
            hasDesktopOpenActions={hasDesktopOpenActions}
            openActionError={openActionError}
            onOpenFile={() => void handleOpenAction("file", item.path)}
            onOpenFolder={() => void handleOpenAction("folder", item.path)}
            openFileLabel={
              isGameContext
                ? t("details.actions.openGameEntry")
                : isSoftwareContext
                  ? t("details.actions.openSoftwareFile")
                  : t("details.actions.openFile")
            }
          />
        </div>
      </div>
    );
  } else {
    content = (
      <div className="details-panel details-inspector details-panel--state">
        <EmptyState
          title={t("details.placeholders.unavailable.title")}
          description={t("details.placeholders.unavailable.description")}
        />
      </div>
    );
  }

  return <section className="panel-card details-panel-card">{content}</section>;
}
