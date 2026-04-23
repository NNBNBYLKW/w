import path from "node:path";

import { app, BrowserWindow, dialog, ipcMain, type OpenDialogOptions } from "electron";


const frontendUrl = process.env.FRONTEND_URL ?? "http://127.0.0.1:5173";
const selectFolderChannel = "asset-workbench:select-folder";
const minimizeWindowChannel = "asset-workbench:minimize-window";
const toggleMaximizeWindowChannel = "asset-workbench:toggle-maximize-window";
const closeWindowChannel = "asset-workbench:close-window";
const getWindowStateChannel = "asset-workbench:get-window-state";
const windowStateChangedChannel = "asset-workbench:window-state-changed";

type WindowStatePayload = {
  isMaximized: boolean;
};

function getWindowStatePayload(window: BrowserWindow | null): WindowStatePayload {
  return {
    isMaximized: window?.isMaximized() ?? false,
  };
}

function emitWindowState(window: BrowserWindow) {
  window.webContents.send(windowStateChangedChannel, getWindowStatePayload(window));
}


function createMainWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 720,
    frame: false,
    autoHideMenuBar: true,
    backgroundColor: "#edf5ff",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      // The preload bridge uses node:fs and node:path to implement desktop open
      // actions, so it must run outside the sandboxed preload environment.
      sandbox: false,
    },
  });

  window.on("maximize", () => {
    emitWindowState(window);
  });

  window.on("unmaximize", () => {
    emitWindowState(window);
  });

  void window.loadURL(frontendUrl);
}


app.whenReady().then(() => {
  ipcMain.handle(selectFolderChannel, async () => {
    const ownerWindow = BrowserWindow.getFocusedWindow();
    const options: OpenDialogOptions = {
      properties: ["openDirectory"],
      title: "Choose source folder",
    };
    const result = ownerWindow
      ? await dialog.showOpenDialog(ownerWindow, options)
      : await dialog.showOpenDialog(options);

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    return result.filePaths[0] ?? null;
  });

  ipcMain.handle(minimizeWindowChannel, (event) => {
    const ownerWindow = BrowserWindow.fromWebContents(event.sender);
    ownerWindow?.minimize();
  });

  ipcMain.handle(toggleMaximizeWindowChannel, (event) => {
    const ownerWindow = BrowserWindow.fromWebContents(event.sender);
    if (!ownerWindow) {
      return getWindowStatePayload(null);
    }

    if (ownerWindow.isMaximized()) {
      ownerWindow.unmaximize();
    } else {
      ownerWindow.maximize();
    }

    return getWindowStatePayload(ownerWindow);
  });

  ipcMain.handle(closeWindowChannel, (event) => {
    const ownerWindow = BrowserWindow.fromWebContents(event.sender);
    ownerWindow?.close();
  });

  ipcMain.handle(getWindowStateChannel, (event) => {
    const ownerWindow = BrowserWindow.fromWebContents(event.sender);
    return getWindowStatePayload(ownerWindow);
  });

  createMainWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
