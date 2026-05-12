export function hasDesktopDropPathBridge(): boolean {
  return typeof getDropBridge()?.getDroppedFilePath === "function";
}


export function getDroppedFilePath(file: File): string | null {
  return getDropBridge()?.getDroppedFilePath?.(file) ?? null;
}


function getDropBridge():
  | {
      getDroppedFilePath?: (file: File) => string | null;
    }
  | undefined {
  return (
    window as typeof window & {
      assetWorkbench?: {
        getDroppedFilePath?: (file: File) => string | null;
      };
    }
  ).assetWorkbench;
}
