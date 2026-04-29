"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_path_1 = __importDefault(require("node:path"));
const node_fs_1 = __importDefault(require("node:fs"));
const node_http_1 = __importDefault(require("node:http"));
const node_child_process_1 = require("node:child_process");
const electron_1 = require("electron");
const frontendUrl = process.env.FRONTEND_URL ?? "http://127.0.0.1:5173";
const packagedBackendUrl = "http://127.0.0.1:8765";
const selectFolderChannel = "asset-workbench:select-folder";
const minimizeWindowChannel = "asset-workbench:minimize-window";
const toggleMaximizeWindowChannel = "asset-workbench:toggle-maximize-window";
const closeWindowChannel = "asset-workbench:close-window";
const getWindowStateChannel = "asset-workbench:get-window-state";
const windowStateChangedChannel = "asset-workbench:window-state-changed";
electron_1.app.setName("Workbench Beta");
let mainWindow = null;
let backendProcess = null;
let backendLogStream = null;
if (electron_1.app.isPackaged && !process.env.BACKEND_URL) {
    process.env.BACKEND_URL = packagedBackendUrl;
}
function getWindowStatePayload(window) {
    return {
        isMaximized: window?.isMaximized() ?? false,
    };
}
function emitWindowState(window) {
    window.webContents.send(windowStateChangedChannel, getWindowStatePayload(window));
}
function getFrontendIndexPath() {
    return node_path_1.default.join(process.resourcesPath, "frontend", "dist", "index.html");
}
function getPackagedBackendPath() {
    return node_path_1.default.join(process.resourcesPath, "backend", "workbench-backend.exe");
}
function getBundledFfmpegPath() {
    return node_path_1.default.join(process.resourcesPath, "ffmpeg", "ffmpeg.exe");
}
function getBackendLogPath() {
    const logsPath = electron_1.app.getPath("logs");
    node_fs_1.default.mkdirSync(logsPath, { recursive: true });
    return node_path_1.default.join(logsPath, "backend.log");
}
function getBackendDataDir() {
    return node_path_1.default.join(electron_1.app.getPath("userData"), "backend-data");
}
function getHealthUrl(backendUrl) {
    return `${backendUrl.replace(/\/$/, "")}/health`;
}
function checkBackendHealth(backendUrl) {
    const healthUrl = new URL(getHealthUrl(backendUrl));
    return new Promise((resolve) => {
        const request = node_http_1.default.get({
            hostname: healthUrl.hostname,
            port: healthUrl.port,
            path: healthUrl.pathname,
            timeout: 1000,
        }, (response) => {
            response.resume();
            resolve(response.statusCode === 200);
        });
        request.on("timeout", () => {
            request.destroy();
            resolve(false);
        });
        request.on("error", () => {
            resolve(false);
        });
    });
}
async function waitForBackendReady(backendUrl, timeoutMs = 20000) {
    const startedAt = Date.now();
    while (Date.now() - startedAt < timeoutMs) {
        if (await checkBackendHealth(backendUrl)) {
            return true;
        }
        await new Promise((resolve) => {
            setTimeout(resolve, 500);
        });
    }
    return false;
}
function appendBackendLogPrefix(logPath, backendPath, dataDir, ffmpegPath) {
    const header = [
        "",
        `[${new Date().toISOString()}] Starting Workbench backend`,
        `backend=${backendPath}`,
        `data_dir=${dataDir}`,
        `ffmpeg=${ffmpegPath}`,
        "",
    ].join("\n");
    node_fs_1.default.appendFileSync(logPath, header, { encoding: "utf-8" });
}
async function ensurePackagedBackend() {
    if (await checkBackendHealth(packagedBackendUrl)) {
        process.env.BACKEND_URL = packagedBackendUrl;
        return packagedBackendUrl;
    }
    const backendPath = getPackagedBackendPath();
    if (!node_fs_1.default.existsSync(backendPath)) {
        throw new Error(`Packaged backend executable was not found: ${backendPath}`);
    }
    const dataDir = getBackendDataDir();
    const ffmpegPath = getBundledFfmpegPath();
    node_fs_1.default.mkdirSync(dataDir, { recursive: true });
    const logPath = getBackendLogPath();
    appendBackendLogPrefix(logPath, backendPath, dataDir, ffmpegPath);
    backendLogStream = node_fs_1.default.createWriteStream(logPath, { flags: "a" });
    const spawnedBackend = (0, node_child_process_1.spawn)(backendPath, [], {
        cwd: node_path_1.default.dirname(backendPath),
        env: {
            ...process.env,
            WORKBENCH_API_HOST: "127.0.0.1",
            WORKBENCH_API_PORT: "8765",
            WORKBENCH_DATA_DIR: dataDir,
            WORKBENCH_FFMPEG_PATH: ffmpegPath,
        },
        stdio: ["ignore", "pipe", "pipe"],
        windowsHide: true,
    });
    backendProcess = spawnedBackend;
    spawnedBackend.stdout?.pipe(backendLogStream, { end: false });
    spawnedBackend.stderr?.pipe(backendLogStream, { end: false });
    spawnedBackend.on("exit", (code, signal) => {
        backendLogStream?.write(`\n[${new Date().toISOString()}] Backend exited code=${code ?? "null"} signal=${signal ?? "null"}\n`);
        backendProcess = null;
    });
    if (!(await waitForBackendReady(packagedBackendUrl))) {
        throw new Error(`Packaged backend did not become ready. See ${logPath}`);
    }
    process.env.BACKEND_URL = packagedBackendUrl;
    return packagedBackendUrl;
}
function stopBackendProcess() {
    const processToStop = backendProcess;
    backendProcess = null;
    if (!processToStop || processToStop.killed) {
        backendLogStream?.end();
        backendLogStream = null;
        return;
    }
    const pid = processToStop.pid;
    processToStop.kill();
    setTimeout(() => {
        if (processToStop.exitCode === null && pid) {
            (0, node_child_process_1.execFile)("taskkill", ["/PID", String(pid), "/T", "/F"], () => {
                backendLogStream?.end();
                backendLogStream = null;
            });
            return;
        }
        backendLogStream?.end();
        backendLogStream = null;
    }, 3000);
}
function loadStartupPage(window) {
    void window.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(`
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>Starting Workbench</title>
          <style>
            body {
              margin: 0;
              height: 100vh;
              display: grid;
              place-items: center;
              font-family: "Segoe UI", sans-serif;
              color: #16446c;
              background: linear-gradient(135deg, #f7fbff, #eaf5ff);
            }
            main {
              max-width: 480px;
              padding: 28px;
              border: 1px solid #cfe5f8;
              border-radius: 18px;
              background: rgba(255, 255, 255, 0.88);
              box-shadow: 0 20px 60px rgba(58, 110, 150, 0.12);
            }
            p { color: #58748a; line-height: 1.6; }
          </style>
        </head>
        <body>
          <main>
            <h1>Starting Workbench</h1>
            <p>Preparing the local backend and workspace data directory...</p>
          </main>
        </body>
      </html>
    `)}`);
}
function loadBackendErrorPage(window, error) {
    const logPath = getBackendLogPath();
    const message = error instanceof Error ? error.message : String(error);
    void window.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(`
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>Workbench backend failed to start</title>
          <style>
            body {
              margin: 0;
              min-height: 100vh;
              display: grid;
              place-items: center;
              font-family: "Segoe UI", sans-serif;
              color: #5a1f1f;
              background: #fff8f8;
            }
            main {
              max-width: 560px;
              padding: 28px;
              border: 1px solid #f1c7c7;
              border-radius: 18px;
              background: #ffffff;
            }
            code {
              display: block;
              padding: 10px;
              border-radius: 10px;
              color: #34495e;
              background: #f4f7fb;
              word-break: break-all;
            }
          </style>
        </head>
        <body>
          <main>
            <h1>Workbench backend failed to start</h1>
            <p>The app could not start its local backend. Please close Workbench and try again.</p>
            <p>Log file:</p>
            <code>${logPath}</code>
            <p>Reason: ${message}</p>
          </main>
        </body>
      </html>
    `)}`);
}
async function loadFrontend(window) {
    if (process.env.FRONTEND_URL) {
        process.env.BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
        await window.loadURL(frontendUrl);
        return;
    }
    if (electron_1.app.isPackaged) {
        await ensurePackagedBackend();
        await window.loadFile(getFrontendIndexPath());
        return;
    }
    process.env.BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    await window.loadURL(frontendUrl);
}
function createMainWindow() {
    mainWindow = new electron_1.BrowserWindow({
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
    mainWindow.on("maximize", () => {
        if (mainWindow) {
            emitWindowState(mainWindow);
        }
    });
    mainWindow.on("unmaximize", () => {
        if (mainWindow) {
            emitWindowState(mainWindow);
        }
    });
    mainWindow.on("closed", () => {
        mainWindow = null;
    });
    loadStartupPage(mainWindow);
    void loadFrontend(mainWindow).catch((error) => {
        if (mainWindow) {
            loadBackendErrorPage(mainWindow, error);
        }
    });
}
if (!electron_1.app.requestSingleInstanceLock()) {
    electron_1.app.quit();
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
electron_1.app.on("second-instance", () => {
    if (!mainWindow) {
        return;
    }
    if (mainWindow.isMinimized()) {
        mainWindow.restore();
    }
    mainWindow.focus();
});
electron_1.app.on("before-quit", () => {
    stopBackendProcess();
});
electron_1.app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
        electron_1.app.quit();
    }
});
