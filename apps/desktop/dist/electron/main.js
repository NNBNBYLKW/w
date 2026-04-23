"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_path_1 = __importDefault(require("node:path"));
const electron_1 = require("electron");
const frontendUrl = process.env.FRONTEND_URL ?? "http://127.0.0.1:5173";
const selectFolderChannel = "asset-workbench:select-folder";
const minimizeWindowChannel = "asset-workbench:minimize-window";
const toggleMaximizeWindowChannel = "asset-workbench:toggle-maximize-window";
const closeWindowChannel = "asset-workbench:close-window";
const getWindowStateChannel = "asset-workbench:get-window-state";
const windowStateChangedChannel = "asset-workbench:window-state-changed";
function getWindowStatePayload(window) {
    return {
        isMaximized: window?.isMaximized() ?? false,
    };
}
function emitWindowState(window) {
    window.webContents.send(windowStateChangedChannel, getWindowStatePayload(window));
}
function createMainWindow() {
    const window = new electron_1.BrowserWindow({
        width: 1440,
        height: 920,
        minWidth: 1100,
        minHeight: 720,
        frame: false,
        autoHideMenuBar: true,
        backgroundColor: "#edf5ff",
        webPreferences: {
            preload: node_path_1.default.join(__dirname, "preload.js"),
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
electron_1.app.whenReady().then(() => {
    electron_1.ipcMain.handle(selectFolderChannel, async () => {
        const ownerWindow = electron_1.BrowserWindow.getFocusedWindow();
        const options = {
            properties: ["openDirectory"],
            title: "Choose source folder",
        };
        const result = ownerWindow
            ? await electron_1.dialog.showOpenDialog(ownerWindow, options)
            : await electron_1.dialog.showOpenDialog(options);
        if (result.canceled || result.filePaths.length === 0) {
            return null;
        }
        return result.filePaths[0] ?? null;
    });
    electron_1.ipcMain.handle(minimizeWindowChannel, (event) => {
        const ownerWindow = electron_1.BrowserWindow.fromWebContents(event.sender);
        ownerWindow?.minimize();
    });
    electron_1.ipcMain.handle(toggleMaximizeWindowChannel, (event) => {
        const ownerWindow = electron_1.BrowserWindow.fromWebContents(event.sender);
        if (!ownerWindow) {
            return getWindowStatePayload(null);
        }
        if (ownerWindow.isMaximized()) {
            ownerWindow.unmaximize();
        }
        else {
            ownerWindow.maximize();
        }
        return getWindowStatePayload(ownerWindow);
    });
    electron_1.ipcMain.handle(closeWindowChannel, (event) => {
        const ownerWindow = electron_1.BrowserWindow.fromWebContents(event.sender);
        ownerWindow?.close();
    });
    electron_1.ipcMain.handle(getWindowStateChannel, (event) => {
        const ownerWindow = electron_1.BrowserWindow.fromWebContents(event.sender);
        return getWindowStatePayload(ownerWindow);
    });
    createMainWindow();
    electron_1.app.on("activate", () => {
        if (electron_1.BrowserWindow.getAllWindows().length === 0) {
            createMainWindow();
        }
    });
});
electron_1.app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
        electron_1.app.quit();
    }
});
