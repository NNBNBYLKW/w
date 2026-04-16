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
};


function getAssetWorkbenchBridge(): AssetWorkbenchBridge | null {
  const assetWorkbench = (
    window as typeof window & {
      assetWorkbench?: AssetWorkbenchBridge;
    }
  ).assetWorkbench;

  if (!assetWorkbench?.openFile || !assetWorkbench?.openContainingFolder) {
    return null;
  }

  return assetWorkbench;
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
