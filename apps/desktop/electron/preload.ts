import { contextBridge, ipcRenderer, shell, webUtils } from "electron";


const defaultBackendBaseUrl = "http://127.0.0.1:8000";
const selectFolderChannel = "asset-workbench:select-folder";
const selectFilesChannel = "asset-workbench:select-files";
const minimizeWindowChannel = "asset-workbench:minimize-window";
const toggleMaximizeWindowChannel = "asset-workbench:toggle-maximize-window";
const closeWindowChannel = "asset-workbench:close-window";
const getWindowStateChannel = "asset-workbench:get-window-state";
const windowStateChangedChannel = "asset-workbench:window-state-changed";
const openContainingFolderChannel = "asset-workbench:open-containing-folder";

type WindowStatePayload = {
  isMaximized: boolean;
};


type OpenActionResult =
  | {
      ok: true;
    }
  | {
      ok: false;
      reason: string;
    };


function normalizeInputPath(value: string): string | null {
  const normalized = value.trim().replace(/\//g, "\\");
  return normalized || null;
}


async function openFile(filePath: string): Promise<OpenActionResult> {
  const normalizedPath = normalizeInputPath(filePath);
  if (!normalizedPath) {
    return {
      ok: false,
      reason: "A usable file path is required.",
    };
  }

  const errorMessage = await shell.openPath(normalizedPath);
  if (errorMessage) {
    return {
      ok: false,
      reason: errorMessage,
    };
  }

  return { ok: true };
}


async function openContainingFolder(filePath: string): Promise<OpenActionResult> {
  return ipcRenderer.invoke(openContainingFolderChannel, filePath);
}


contextBridge.exposeInMainWorld("assetWorkbench", {
  getBackendBaseUrl: () => process.env.BACKEND_URL ?? defaultBackendBaseUrl,
  selectFolder: async (): Promise<string | null> => ipcRenderer.invoke(selectFolderChannel),
  selectFiles: async (): Promise<string[]> => ipcRenderer.invoke(selectFilesChannel),
  getDroppedFilePath: (file: unknown): string | null => {
    const getPathForFile = (webUtils as { getPathForFile?: (file: unknown) => string }).getPathForFile;
    if (!getPathForFile) {
      return null;
    }
    const filePath = getPathForFile(file);
    return typeof filePath === "string" && filePath.trim() ? filePath : null;
  },
  openFile,
  openContainingFolder,
  minimizeWindow: async (): Promise<void> => ipcRenderer.invoke(minimizeWindowChannel),
  toggleMaximizeWindow: async (): Promise<WindowStatePayload> => ipcRenderer.invoke(toggleMaximizeWindowChannel),
  closeWindow: async (): Promise<void> => ipcRenderer.invoke(closeWindowChannel),
  getWindowState: async (): Promise<WindowStatePayload> => ipcRenderer.invoke(getWindowStateChannel),
  onWindowStateChange: (callback: (payload: WindowStatePayload) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, payload: WindowStatePayload) => {
      callback(payload);
    };

    ipcRenderer.on(windowStateChangedChannel, listener);

    return () => {
      ipcRenderer.off(windowStateChangedChannel, listener);
    };
  },
});
