"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_path_1 = __importDefault(require("node:path"));
const electron_1 = require("electron");
const frontendUrl = process.env.FRONTEND_URL ?? "http://127.0.0.1:5173";
const selectFolderChannel = "asset-workbench:select-folder";
function createMainWindow() {
    const window = new electron_1.BrowserWindow({
        width: 1440,
        height: 920,
        minWidth: 1100,
        minHeight: 720,
        backgroundColor: "#0d1117",
        webPreferences: {
            preload: node_path_1.default.join(__dirname, "preload.js"),
            contextIsolation: true,
            nodeIntegration: false,
            // The preload bridge uses node:fs and node:path to implement desktop open
            // actions, so it must run outside the sandboxed preload environment.
            sandbox: false,
        },
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
