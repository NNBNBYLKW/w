import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import { t } from "../../shared/text";
import type { ColorTagValue, ManualPlacementValue } from "../../entities/file/types";
import { updateFilesColorTagBatch } from "../../services/api/colorTagsApi";
import { attachTagToFilesBatch } from "../../services/api/tagsApi";
import { updateFilesPlacementBatch } from "../../services/api/userMetaApi";
import { invalidateFileOrganizationSurfaces } from "../../services/query/invalidation";


type UseBatchOrganizeActionsOptions = {
  onSuccess: () => void;
};

export function useBatchOrganizeActions({ onSuccess }: UseBatchOrganizeActionsOptions) {
  const queryClient = useQueryClient();
  const pushToast = useUIStore((state) => state.pushToast);

  const addTagMutation = useMutation({
    mutationFn: ({ fileIds, name }: { fileIds: number[]; name: string }) => attachTagToFilesBatch(fileIds, name),
    onSuccess: async (response) => {
      await invalidateFileOrganizationSurfaces(queryClient);
      pushToast(t("features.toasts.tagApplied", { count: response.updated_count, name: response.tag.name }));
      onSuccess();
    },
  });

  const colorTagMutation = useMutation({
    mutationFn: ({ colorTag, fileIds }: { colorTag: ColorTagValue | null; fileIds: number[] }) =>
      updateFilesColorTagBatch(fileIds, colorTag),
    onSuccess: async (response) => {
      await invalidateFileOrganizationSurfaces(queryClient);
      pushToast(
        response.color_tag
          ? t("features.toasts.colorApplied", { color: response.color_tag, count: response.updated_count })
          : t("features.toasts.colorCleared", { count: response.updated_count }),
      );
      onSuccess();
    },
  });

  const placementMutation = useMutation({
    mutationFn: ({ fileIds, manualPlacement }: { fileIds: number[]; manualPlacement: ManualPlacementValue | null }) =>
      updateFilesPlacementBatch(fileIds, manualPlacement),
    onSuccess: async (response) => {
      await invalidateFileOrganizationSurfaces(queryClient);
      pushToast(
        response.manual_placement
          ? t("features.toasts.placementApplied", { count: response.updated_count })
          : t("features.toasts.placementAuto", { count: response.updated_count }),
      );
      onSuccess();
    },
  });

  return {
    applyColorTag: (fileIds: number[], colorTag: ColorTagValue | null) => colorTagMutation.mutate({ colorTag, fileIds }),
    applyPlacement: (fileIds: number[], manualPlacement: ManualPlacementValue | null) =>
      placementMutation.mutate({ fileIds, manualPlacement }),
    applyTag: (fileIds: number[], name: string) => addTagMutation.mutate({ fileIds, name }),
    isApplyingColorTag: colorTagMutation.isPending,
    isApplyingPlacement: placementMutation.isPending,
    isApplyingTag: addTagMutation.isPending,
  };
}
