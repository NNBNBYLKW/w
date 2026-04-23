export type DesktopWindowState = {
  isMaximized: boolean;
};

type AssetWorkbenchWindowControlsBridge = {
  minimizeWindow?: () => Promise<void>;
  toggleMaximizeWindow?: () => Promise<DesktopWindowState>;
  closeWindow?: () => Promise<void>;
  getWindowState?: () => Promise<DesktopWindowState>;
  onWindowStateChange?: (callback: (payload: DesktopWindowState) => void) => (() => void) | void;
};

function getWindowControlsBridge(): AssetWorkbenchWindowControlsBridge | null {
  if (typeof window === "undefined") {
    return null;
  }

  const assetWorkbench = (
    window as typeof window & {
      assetWorkbench?: AssetWorkbenchWindowControlsBridge;
    }
  ).assetWorkbench;

  if (
    !assetWorkbench?.minimizeWindow ||
    !assetWorkbench?.toggleMaximizeWindow ||
    !assetWorkbench?.closeWindow ||
    !assetWorkbench?.getWindowState
  ) {
    return null;
  }

  return assetWorkbench;
}

export function hasDesktopWindowControlsBridge(): boolean {
  return getWindowControlsBridge() !== null;
}

export async function getDesktopWindowState(): Promise<DesktopWindowState> {
  const bridge = getWindowControlsBridge();
  if (!bridge?.getWindowState) {
    return { isMaximized: false };
  }

  return bridge.getWindowState();
}

export async function minimizeDesktopWindow(): Promise<void> {
  const bridge = getWindowControlsBridge();
  if (!bridge?.minimizeWindow) {
    return;
  }

  await bridge.minimizeWindow();
}

export async function toggleDesktopWindowMaximize(): Promise<DesktopWindowState> {
  const bridge = getWindowControlsBridge();
  if (!bridge?.toggleMaximizeWindow) {
    return { isMaximized: false };
  }

  return bridge.toggleMaximizeWindow();
}

export async function closeDesktopWindow(): Promise<void> {
  const bridge = getWindowControlsBridge();
  if (!bridge?.closeWindow) {
    return;
  }

  await bridge.closeWindow();
}

export function subscribeToDesktopWindowState(
  callback: (payload: DesktopWindowState) => void,
): () => void {
  const bridge = getWindowControlsBridge();
  if (!bridge?.onWindowStateChange) {
    return () => {};
  }

  const unsubscribe = bridge.onWindowStateChange(callback);
  return typeof unsubscribe === "function" ? unsubscribe : () => {};
}
