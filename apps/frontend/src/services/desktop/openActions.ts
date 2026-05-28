export type OpenActionResult =
  | {
      ok: true;
    }
  | {
      ok: false;
      reason: string;
    };


type AssetWorkbenchBridge = {
  openFile?: (path: string) => Promise<OpenActionResult>;
  openContainingFolder?: (path: string) => Promise<OpenActionResult>;
  showItemInFolder?: (path: string) => Promise<void>;
};

type AvailableAssetWorkbenchBridge = {
  openFile: (path: string) => Promise<OpenActionResult>;
  openContainingFolder: (path: string) => Promise<OpenActionResult>;
  showItemInFolder: (path: string) => Promise<void>;
};

function getAssetWorkbenchBridge(): AvailableAssetWorkbenchBridge | null {
  const assetWorkbench = (
    window as typeof window & {
      assetWorkbench?: AssetWorkbenchBridge;
    }
  ).assetWorkbench;

  if (
    typeof assetWorkbench?.openFile !== "function" ||
    typeof assetWorkbench.openContainingFolder !== "function"
  ) {
    return null;
  }

  return {
    openFile: assetWorkbench.openFile,
    openContainingFolder: assetWorkbench.openContainingFolder,
    showItemInFolder: typeof assetWorkbench.showItemInFolder === "function"
      ? assetWorkbench.showItemInFolder
      : async () => {},
  };
}


export function normalizeIndexedFilePath(value: string | null | undefined): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim();
  return normalized || null;
}


export function hasDesktopOpenActionsBridge(): boolean {
  return getAssetWorkbenchBridge() !== null;
}


export async function openIndexedFile(path: string): Promise<OpenActionResult> {
  const bridge = getAssetWorkbenchBridge();
  if (!bridge) {
    return {
      ok: false,
      reason: "Desktop open actions are unavailable outside the desktop shell.",
    };
  }

  return bridge.openFile(path);
}


export async function showItemInFolder(path: string): Promise<void> {
  const bridge = getAssetWorkbenchBridge();
  if (!bridge) {
    return;
  }
  await bridge.showItemInFolder(path);
}

export async function openIndexedContainingFolder(path: string): Promise<OpenActionResult> {
  const bridge = getAssetWorkbenchBridge();
  if (!bridge) {
    return {
      ok: false,
      reason: "Desktop open actions are unavailable outside the desktop shell.",
    };
  }

  return bridge.openContainingFolder(path);
}
