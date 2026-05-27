import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import type {
  ColorTagValue,
  FileDetailResponseVM,
  FileRatingValue,
  FileStatusValue,
  ManualPlacementValue,
} from "../../../entities/file/types";
import { updateFileColorTag } from "../../../services/api/colorTagsApi";
import {
  normalizeIndexedFilePath,
  openIndexedContainingFolder,
  openIndexedFile,
} from "../../../services/desktop/openActions";
import { invalidateDetailsPanelFileDetail, invalidateFileOrganizationSurfaces } from "../../../services/query/invalidation";
import { updateFileStatus } from "../../../services/api/statusApi";
import { attachTagToFile, removeTagFromFile } from "../../../services/api/tagsApi";
import { updateFilePlacement, updateFileUserMeta } from "../../../services/api/userMetaApi";
import { queryKeys } from "../../../services/query/queryKeys";
import { t } from "../../../shared/text";
import { formatStatusLabel } from "../shared/detailsHelpers";

export type RetrievalHint =
  | { kind: "tag"; message: string }
  | { kind: "color"; message: string }
  | { kind: "status"; message: string }
  | { kind: "placement"; message: string }
  | null;

export function useDetailsMutations(
  queryClient: ReturnType<typeof useQueryClient>,
  parsedFileId: number | null,
  contextFlags: {
    isGameContextForMutations: boolean;
    isBookContextForMutations: boolean;
    isSoftwareContextForMutations: boolean;
  },
) {
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
  const [confirmRemoveTag, setConfirmRemoveTag] = useState<{ id: number; name: string } | null>(null);
  const [retrievalHint, setRetrievalHint] = useState<RetrievalHint>(null);
  const [copied, setCopied] = useState(false);

  const { isGameContextForMutations, isBookContextForMutations, isSoftwareContextForMutations } = contextFlags;

  const handleCopyPath = async (filePath: string) => {
    try {
      await navigator.clipboard.writeText(filePath);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available
    }
  };

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

  // Reset preview state on selectedItemId change
  useEffect(() => {
    setPreviewLoadFailed(false);
    setSinglePreviewLoaded(false);
    setVideoPreviewFrameIndex(0);
    setVideoPreviewPlaybackFailed(false);
    setCopied(false);
  }, [parsedFileId]);

  // Reset mutation state on selectedItemId change
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
  }, [parsedFileId]);

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

  const isTagMutationPending = addTagMutation.isPending || removeTagMutation.isPending;
  const isColorTagMutationPending = colorTagMutation.isPending;
  const isStatusMutationPending = statusMutation.isPending;
  const isUserMetaMutationPending = userMetaMutation.isPending;
  const isPlacementMutationPending = placementMutation.isPending;
  const isOpenActionPending = pendingOpenAction !== null;

  return {
    tagInput,
    setTagInput,
    tagMutationError,
    colorTagMutationError,
    statusMutationError,
    userMetaMutationError,
    placementMutationError,
    openActionError,
    pendingOpenAction,
    previewLoadFailed,
    setPreviewLoadFailed,
    singlePreviewLoaded,
    setSinglePreviewLoaded,
    videoPreviewFrameIndex,
    setVideoPreviewFrameIndex,
    videoPreviewPlaybackFailed,
    setVideoPreviewPlaybackFailed,
    confirmRemoveTag,
    setConfirmRemoveTag,
    retrievalHint,
    copied,
    isTagMutationPending,
    isColorTagMutationPending,
    isStatusMutationPending,
    isUserMetaMutationPending,
    isPlacementMutationPending,
    isOpenActionPending,
    addTagMutation,
    removeTagMutation,
    colorTagMutation,
    statusMutation,
    userMetaMutation,
    placementMutation,
    handleCopyPath,
    handleOpenAction,
  };
}
