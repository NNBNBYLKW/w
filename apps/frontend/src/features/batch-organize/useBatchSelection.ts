import { useEffect, useState } from "react";

import { useUIStore } from "../../app/providers/uiStore";


type UseBatchSelectionOptions = {
  pageLabel: string;
  resetDeps: ReadonlyArray<unknown>;
};

export function useBatchSelection({ pageLabel, resetDeps }: UseBatchSelectionOptions) {
  const selectItem = useUIStore((state) => state.selectItem);
  const setBatchSelectionSummary = useUIStore((state) => state.setBatchSelectionSummary);
  const [isBatchMode, setIsBatchMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  useEffect(() => {
    if (!isBatchMode) {
      setBatchSelectionSummary(null);
      return;
    }

    setBatchSelectionSummary({
      pageLabel,
      selectedCount: selectedIds.length,
    });
  }, [isBatchMode, pageLabel, selectedIds.length, setBatchSelectionSummary]);

  useEffect(() => {
    if (!isBatchMode) {
      return;
    }

    setSelectedIds([]);
  }, [isBatchMode, ...resetDeps]);

  useEffect(() => () => setBatchSelectionSummary(null), [setBatchSelectionSummary]);

  const enterBatchMode = () => {
    selectItem(null);
    setSelectedIds([]);
    setIsBatchMode(true);
  };

  const exitBatchMode = () => {
    setSelectedIds([]);
    setIsBatchMode(false);
    setBatchSelectionSummary(null);
  };

  const clearSelection = () => {
    setSelectedIds([]);
  };

  const toggleSelection = (fileId: number) => {
    setSelectedIds((current) =>
      current.includes(fileId) ? current.filter((id) => id !== fileId) : [...current, fileId],
    );
  };

  return {
    clearSelection,
    enterBatchMode,
    exitBatchMode,
    isBatchMode,
    isSelected: (fileId: number) => selectedIds.includes(fileId),
    selectedCount: selectedIds.length,
    selectedIds,
    toggleSelection,
  };
}
