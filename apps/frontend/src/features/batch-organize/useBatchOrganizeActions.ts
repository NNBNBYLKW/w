import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useUIStore } from "../../app/providers/uiStore";
import type { ColorTagValue } from "../../entities/file/types";
import { updateFilesColorTagBatch } from "../../services/api/colorTagsApi";
import { attachTagToFilesBatch } from "../../services/api/tagsApi";
import { queryKeys } from "../../services/query/queryKeys";


type UseBatchOrganizeActionsOptions = {
  onSuccess: () => void;
};

export function useBatchOrganizeActions({ onSuccess }: UseBatchOrganizeActionsOptions) {
  const queryClient = useQueryClient();
  const pushToast = useUIStore((state) => state.pushToast);

  const invalidateQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.tags }),
      queryClient.invalidateQueries({ queryKey: ["tag-files"] }),
      queryClient.invalidateQueries({ queryKey: ["recent"] }),
      queryClient.invalidateQueries({ queryKey: ["recent-tagged"] }),
      queryClient.invalidateQueries({ queryKey: ["recent-color-tagged"] }),
      queryClient.invalidateQueries({ queryKey: ["media-library"] }),
      queryClient.invalidateQueries({ queryKey: ["books-list"] }),
      queryClient.invalidateQueries({ queryKey: ["games-list"] }),
      queryClient.invalidateQueries({ queryKey: ["software-list"] }),
      queryClient.invalidateQueries({ queryKey: queryKeys.collections }),
      queryClient.invalidateQueries({ queryKey: ["collection-files"] }),
      queryClient.invalidateQueries({ queryKey: ["search"] }),
      queryClient.invalidateQueries({ queryKey: ["files-list"] }),
    ]);
  };

  const addTagMutation = useMutation({
    mutationFn: ({ fileIds, name }: { fileIds: number[]; name: string }) => attachTagToFilesBatch(fileIds, name),
    onSuccess: async (response) => {
      await invalidateQueries();
      pushToast(`Applied tag "${response.tag.name}" to ${response.updated_count} files.`);
      onSuccess();
    },
  });

  const colorTagMutation = useMutation({
    mutationFn: ({ colorTag, fileIds }: { colorTag: ColorTagValue | null; fileIds: number[] }) =>
      updateFilesColorTagBatch(fileIds, colorTag),
    onSuccess: async (response) => {
      await invalidateQueries();
      pushToast(
        response.color_tag
          ? `Applied ${response.color_tag} color tag to ${response.updated_count} files.`
          : `Cleared color tag on ${response.updated_count} files.`,
      );
      onSuccess();
    },
  });

  return {
    applyColorTag: (fileIds: number[], colorTag: ColorTagValue | null) => colorTagMutation.mutate({ colorTag, fileIds }),
    applyTag: (fileIds: number[], name: string) => addTagMutation.mutate({ fileIds, name }),
    isApplyingColorTag: colorTagMutation.isPending,
    isApplyingTag: addTagMutation.isPending,
  };
}
