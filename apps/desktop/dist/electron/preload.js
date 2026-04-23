"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_fs_1 = __importDefault(require("node:fs"));
const node_path_1 = __importDefault(require("node:path"));
const electron_1 = require("electron");
const backendBaseUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
const selectFolderChannel = "asset-workbench:select-folder";
const minimizeWindowChannel = "asset-workbench:minimize-window";
const toggleMaximizeWindowChannel = "asset-workbench:toggle-maximize-window";
const closeWindowChannel = "asset-workbench:close-window";
const getWindowStateChannel = "asset-workbench:get-window-state";
const windowStateChangedChannel = "asset-workbench:window-state-changed";
function normalizeInputPath(value) {
    const normalized = value.trim().replace(/\//g, "\\");
    return normalized || null;
}
function deriveContainingFolderPath(filePath) {
    const normalizedPath = normalizeInputPath(filePath);
    if (!normalizedPath) {
        return null;
    }
    const parentDirectory = node_path_1.default.win32.dirname(normalizedPath);
    if (!parentDirectory || parentDirectory === "." || parentDirectory === normalizedPath) {
        return null;
    }
    return parentDirectory;
}
async function openFile(filePath) {
    const normalizedPath = normalizeInputPath(filePath);
    if (!normalizedPath) {
        return {
            ok: false,
            reason: "A usable file path is required.",
        };
    }
    const errorMessage = await electron_1.shell.openPath(normalizedPath);
    if (errorMessage) {
        return {
            ok: false,
            reason: errorMessage,
        };
    }
    return { ok: true };
}
async function openContainingFolder(filePath) {
    const parentDirectory = deriveContainingFolderPath(filePath);
    if (!parentDirectory) {
        return {
            ok: false,
            reason: "A containing folder could not be derived from this file path.",
        };
    }
    if (!node_fs_1.default.existsSync(parentDirectory)) {
        return {
            ok: false,
            reason: "The containing folder does not exist.",
        };
    }
    try {
        if (!node_fs_1.default.statSync(parentDirectory).isDirectory()) {
            return {
                ok: false,
                reason: "The containing folder does not exist.",
            };
        }
    }
    catch {
        return {
            ok: false,
            reason: "The containing folder could not be verified.",
        };
    }
    const errorMessage = await electron_1.shell.openPath(parentDirectory);
    if (errorMessage) {
        return {
            ok: false,
            reason: errorMessage,
        };
    }
    return { ok: true };
}
electron_1.contextBridge.exposeInMainWorld("assetWorkbench", {
    getBackendBaseUrl: () => backendBaseUrl,
    selectFolder: async () => electron_1.ipcRenderer.invoke(selectFolderChannel),
    openFile,
    openContainingFolder,
    minimizeWindow: async () => electron_1.ipcRenderer.invoke(minimizeWindowChannel),
    toggleMaximizeWindow: async () => electron_1.ipcRenderer.invoke(toggleMaximizeWindowChannel),
    closeWindow: async () => electron_1.ipcRenderer.invoke(closeWindowChannel),
    getWindowState: async () => electron_1.ipcRenderer.invoke(getWindowStateChannel),
    onWindowStateChange: (callback) => {
        const listener = (_event, payload) => {
            callback(payload);
        };
        electron_1.ipcRenderer.on(windowStateChangedChannel, listener);
        return () => {
            electron_1.ipcRenderer.off(windowStateChangedChannel, listener);
        };
    },
});
