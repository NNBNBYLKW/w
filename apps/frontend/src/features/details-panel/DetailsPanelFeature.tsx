import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import type { ColorTagValue, FileRatingValue, FileStatusValue } from "../../entities/file/types";

import { useUIStore } from "../../app/providers/uiStore";
import { t, useLocale } from "../../shared/text";
import { useRetryingThumbnail, useThumbnailWarmup } from "../../shared/ui/thumbnail";
import { getFileDetails, getFileThumbnailUrl, getFileVideoPreview, getFileVideoPreviewFrameUrl } from "../../services/api/fileDetailsApi";
import { hasDesktopOpenActionsBridge, showItemInFolder as desktopShowItemInFolder } from "../../services/desktop/openActions";
import { queryKeys } from "../../services/query/queryKeys";
import { inferBookFormat, inferGameEntry, inferSoftwareFormat } from "./shared/detailsHelpers";
import { useDetailsMutations } from "./hooks/useDetailsMutations";
import { DetailsPanelBody } from "./DetailsPanelBody";

export function DetailsPanelFeature() {
  useLocale();
  const selectedItemId = useUIStore((state) => state.selectedItemId);
  const batchSelectionSummary = useUIStore((state) => state.batchSelectionSummary);
  const selectItem = useUIStore((state) => state.selectItem);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();

  const parsedFileId = selectedItemId !== null ? Number(selectedItemId) : null;
  const hasInvalidSelectedId =
    selectedItemId !== null && (!Number.isInteger(parsedFileId) || parsedFileId === null || parsedFileId <= 0);
  const hasDesktopOpenActions = hasDesktopOpenActionsBridge();
  const isGamesRoute = location.pathname.startsWith("/library/games");
  const isBooksRoute = location.pathname.startsWith("/books") || location.pathname.startsWith("/library/books");
  const isSoftwareRoute = location.pathname.startsWith("/software");

  const detailQuery = useQuery({
    queryKey: parsedFileId !== null ? queryKeys.fileDetail(parsedFileId) : ["file-detail", "idle"],
    queryFn: () => getFileDetails(parsedFileId as number),
    enabled: parsedFileId !== null && !hasInvalidSelectedId,
    staleTime: 30000,
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

  const mutations = useDetailsMutations(queryClient, parsedFileId, {
    isGameContextForMutations,
    isBookContextForMutations,
    isSoftwareContextForMutations,
  });

  const videoPreviewQuery = useQuery({
    queryKey: parsedFileId !== null ? ["file-video-preview", parsedFileId] : ["file-video-preview", "idle"],
    queryFn: () => getFileVideoPreview(parsedFileId as number),
    enabled:
      parsedFileId !== null &&
      !hasInvalidSelectedId &&
      currentItem?.file_type === "video" &&
      mutations.singlePreviewLoaded &&
      !mutations.previewLoadFailed &&
      !mutations.videoPreviewPlaybackFailed,
    retry: false,
  });

  const videoPreviewFrameIndexes = videoPreviewQuery.data?.item.frame_indexes ?? [];
  const isVideoPreviewActive =
    currentItem?.file_type === "video" &&
    !mutations.videoPreviewPlaybackFailed &&
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
      mutations.setVideoPreviewFrameIndex(0);
      return;
    }

    const intervalId = window.setInterval(() => {
      mutations.setVideoPreviewFrameIndex((current: number) => (current + 1) % videoPreviewFrameIndexes.length);
    }, 800);

    return () => window.clearInterval(intervalId);
  }, [isVideoPreviewActive, videoPreviewFrameIndexes.length]);

  const item = detailQuery.data?.item;
  const isImageFile = item?.file_type === "image";
  const isVideoFile = item?.file_type === "video";
  const isMediaFile = isImageFile || isVideoFile;
  const inferredBookFormat = item ? inferBookFormat(item.name, item.path) : null;
  const inferredSoftwareFormat = item ? inferSoftwareFormat(item.name, item.path) : null;
  const inferredGameEntry = item ? inferGameEntry(item.name, item.path) : false;
  const isBookContext = isBooksRoute || inferredBookFormat !== null;
  const isGameContext = isGamesRoute || inferredGameEntry || (item?.status ?? null) !== null;
  const isSoftwareContext = !isGameContext && (isSoftwareRoute || inferredSoftwareFormat !== null);
  const isExeSoftwareFile = isSoftwareContext && inferredSoftwareFormat === "exe";
  const isPdfBookFile = isBookContext && inferredBookFormat === "pdf";
  const metadata = item?.metadata;
  const firstTag = item?.tags[0] ?? null;
  const activeVideoPreviewFrameIndex = videoPreviewFrameIndexes[mutations.videoPreviewFrameIndex] ?? videoPreviewFrameIndexes[0];
  const previewImageSrc =
    isVideoPreviewActive && activeVideoPreviewFrameIndex !== undefined
      ? getFileVideoPreviewFrameUrl(item?.id ?? 0, activeVideoPreviewFrameIndex)
      : previewThumbnail.imageSrc;

  const handleConfirmRemoveTag = () => {
    mutations.removeTagMutation.mutate(mutations.confirmRemoveTag!.id);
    mutations.setConfirmRemoveTag(null);
  };

  const handleOnRemoveTag = (tagId: number) => {
    const tag = detailQuery.data?.item.tags.find((t: any) => t.id === tagId);
    mutations.setConfirmRemoveTag(tag ? { id: tagId, name: tag.name } : { id: tagId, name: String(tagId) });
  };

  return (
    <section className="panel-card details-panel-card">
      <DetailsPanelBody
        batchSelectionSummary={batchSelectionSummary}
        selectedItemId={selectedItemId}
        hasInvalidSelectedId={hasInvalidSelectedId}
        detailQuery={detailQuery}
        isGamesRoute={isGamesRoute}
        isBooksRoute={isBooksRoute}
        isSoftwareRoute={isSoftwareRoute}
        tagInput={mutations.tagInput}
        onTagInputChange={mutations.setTagInput}
        tagMutationError={mutations.tagMutationError}
        colorTagMutationError={mutations.colorTagMutationError}
        statusMutationError={mutations.statusMutationError}
        userMetaMutationError={mutations.userMetaMutationError}
        placementMutationError={mutations.placementMutationError}
        isTagMutationPending={mutations.isTagMutationPending}
        isColorTagMutationPending={mutations.isColorTagMutationPending}
        isStatusMutationPending={mutations.isStatusMutationPending}
        isUserMetaMutationPending={mutations.isUserMetaMutationPending}
        isPlacementMutationPending={mutations.isPlacementMutationPending}
        isOpenActionPending={mutations.isOpenActionPending}
        hasDesktopOpenActions={hasDesktopOpenActions}
        openActionError={mutations.openActionError}
        onOpenFile={() => void mutations.handleOpenAction("file", item?.path)}
        onOpenFolder={() => void mutations.handleOpenAction("folder", item?.path)}
        onShowInFolder={() => {
          const normalizedPath = item?.path;
          if (normalizedPath) {
            void desktopShowItemInFolder(normalizedPath);
          }
        }}
        onAddTag={(event: React.FormEvent) => {
          event.preventDefault();
          mutations.addTagMutation.mutate(mutations.tagInput);
        }}
        onRemoveTag={handleOnRemoveTag}
        onToggleFavorite={() => mutations.userMetaMutation.mutate({ is_favorite: !item?.is_favorite })}
        onSetRating={(value: FileRatingValue) => mutations.userMetaMutation.mutate({ rating: value })}
        onClearRating={() => mutations.userMetaMutation.mutate({ rating: null })}
        onNotesSave={(notes: string | null) => mutations.userMetaMutation.mutate({ notes })}
        onPlacementChange={(value: string) =>
          mutations.placementMutation.mutate(value === "auto" ? null : (value as any))
        }
        onStatusChange={(value: FileStatusValue) => mutations.statusMutation.mutate(value)}
        onColorTagChange={(value: ColorTagValue | null) => mutations.colorTagMutation.mutate(value)}
        onCopyPath={() => mutations.handleCopyPath(item?.path ?? "")}
        copied={mutations.copied}
        onSelectFile={(fileId: number) => selectItem(String(fileId))}
        previewLoadFailed={mutations.previewLoadFailed}
        previewImageSrc={previewImageSrc}
        isVideoPreviewActive={isVideoPreviewActive}
        isImageFile={isImageFile}
        isVideoFile={isVideoFile}
        isMediaFile={isMediaFile}
        isExeSoftwareFile={isExeSoftwareFile}
        isPdfBookFile={isPdfBookFile}
        isBookContext={isBookContext}
        isGameContext={isGameContext}
        isSoftwareContext={isSoftwareContext}
        inferredBookFormat={inferredBookFormat}
        inferredSoftwareFormat={inferredSoftwareFormat}
        metadata={metadata}
        firstTag={firstTag}
        previewRef={previewThumbnail.ref}
        onPreviewImageError={() => {
          if (isVideoPreviewActive) {
            mutations.setVideoPreviewPlaybackFailed(true);
            return;
          }
          previewThumbnail.onError();
        }}
        onPreviewImageLoad={() => {
          if (!isVideoPreviewActive) {
            mutations.setSinglePreviewLoaded(true);
            previewThumbnail.onLoad();
          }
        }}
        confirmRemoveTag={mutations.confirmRemoveTag}
        onConfirmRemoveTag={handleConfirmRemoveTag}
        onCancelRemoveTag={() => mutations.setConfirmRemoveTag(null)}
        retrievalHint={mutations.retrievalHint}
        openFileLabel={
          isGameContext
            ? t("details.actions.openGameEntry")
            : isSoftwareContext
              ? t("details.actions.openSoftwareFile")
              : t("details.actions.openFile")
        }
      />
    </section>
  );
}
