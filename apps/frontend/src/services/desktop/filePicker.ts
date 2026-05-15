type AssetWorkbenchBridge = {
  selectFiles?: () => Promise<string[]>;
  selectFolder?: () => Promise<string | null>;
};

function getBridge(): AssetWorkbenchBridge | null {
  const w = window as typeof window & {
    assetWorkbench?: AssetWorkbenchBridge;
  };
  return w.assetWorkbench ?? null;
}

export function hasDesktopFilePicker(): boolean {
  const bridge = getBridge();
  return typeof bridge?.selectFiles === "function";
}

export async function selectImportFiles(): Promise<string[]> {
  const bridge = getBridge();
  if (typeof bridge?.selectFiles !== "function") {
    return [];
  }
  try {
    return await bridge.selectFiles();
  } catch {
    return [];
  }
}

export async function selectImportFolder(): Promise<string | null> {
  const bridge = getBridge();
  if (typeof bridge?.selectFolder !== "function") {
    return null;
  }
  try {
    return await bridge.selectFolder();
  } catch {
    return null;
  }
}
