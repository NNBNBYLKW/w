import path from "node:path";
import fs from "node:fs";
import http from "node:http";
import { execFile, spawn, type ChildProcess } from "node:child_process";

import { app, BrowserWindow, dialog, ipcMain, type OpenDialogOptions } from "electron";


const frontendUrl = process.env.FRONTEND_URL ?? "http://127.0.0.1:5173";
const packagedBackendUrl = "http://127.0.0.1:8765";
const selectFolderChannel = "asset-workbench:select-folder";
const minimizeWindowChannel = "asset-workbench:minimize-window";
const toggleMaximizeWindowChannel = "asset-workbench:toggle-maximize-window";
const closeWindowChannel = "asset-workbench:close-window";
const getWindowStateChannel = "asset-workbench:get-window-state";
const windowStateChangedChannel = "asset-workbench:window-state-changed";

app.setName("Workbench Beta");

let mainWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;
let backendLogStream: fs.WriteStream | null = null;

if (app.isPackaged && !process.env.BACKEND_URL) {
  process.env.BACKEND_URL = packagedBackendUrl;
}

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

function getFrontendIndexPath(): string {
  return path.join(process.resourcesPath, "frontend", "dist", "index.html");
}

function getPackagedBackendPath(): string {
  return path.join(process.resourcesPath, "backend", "workbench-backend.exe");
}

function getBundledFfmpegPath(): string {
  return path.join(process.resourcesPath, "ffmpeg", "ffmpeg.exe");
}

function getBackendLogPath(): string {
  const logsPath = app.getPath("logs");
  fs.mkdirSync(logsPath, { recursive: true });
  return path.join(logsPath, "backend.log");
}

function getBackendDataDir(): string {
  return path.join(app.getPath("userData"), "backend-data");
}

function getHealthUrl(backendUrl: string): string {
  return `${backendUrl.replace(/\/$/, "")}/health`;
}

function checkBackendHealth(backendUrl: string): Promise<boolean> {
  const healthUrl = new URL(getHealthUrl(backendUrl));

  return new Promise((resolve) => {
    const request = http.get(
      {
        hostname: healthUrl.hostname,
        port: healthUrl.port,
        path: healthUrl.pathname,
        timeout: 1000,
      },
      (response) => {
        response.resume();
        resolve(response.statusCode === 200);
      },
    );

    request.on("timeout", () => {
      request.destroy();
      resolve(false);
    });

    request.on("error", () => {
      resolve(false);
    });
  });
}

async function waitForBackendReady(backendUrl: string, timeoutMs = 20000): Promise<boolean> {
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

function appendBackendLogPrefix(logPath: string, backendPath: string, dataDir: string, ffmpegPath: string): void {
  const header = [
    "",
    `[${new Date().toISOString()}] Starting Workbench backend`,
    `backend=${backendPath}`,
    `data_dir=${dataDir}`,
    `ffmpeg=${ffmpegPath}`,
    "",
  ].join("\n");
  fs.appendFileSync(logPath, header, { encoding: "utf-8" });
}

async function ensurePackagedBackend(): Promise<string> {
  if (await checkBackendHealth(packagedBackendUrl)) {
    process.env.BACKEND_URL = packagedBackendUrl;
    return packagedBackendUrl;
  }

  const backendPath = getPackagedBackendPath();
  if (!fs.existsSync(backendPath)) {
    throw new Error(`Packaged backend executable was not found: ${backendPath}`);
  }

  const dataDir = getBackendDataDir();
  const ffmpegPath = getBundledFfmpegPath();
  fs.mkdirSync(dataDir, { recursive: true });

  const logPath = getBackendLogPath();
  appendBackendLogPrefix(logPath, backendPath, dataDir, ffmpegPath);
  backendLogStream = fs.createWriteStream(logPath, { flags: "a" });

  const spawnedBackend = spawn(backendPath, [], {
    cwd: path.dirname(backendPath),
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

function stopBackendProcess(): void {
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
      execFile("taskkill", ["/PID", String(pid), "/T", "/F"], () => {
        backendLogStream?.end();
        backendLogStream = null;
      });
      return;
    }

    backendLogStream?.end();
    backendLogStream = null;
  }, 3000);
}

function loadStartupPage(window: BrowserWindow): void {
  void window.loadURL(
    `data:text/html;charset=utf-8,${encodeURIComponent(`
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
    `)}`,
  );
}

function loadBackendErrorPage(window: BrowserWindow, error: unknown): void {
  const logPath = getBackendLogPath();
  const message = error instanceof Error ? error.message : String(error);
  void window.loadURL(
    `data:text/html;charset=utf-8,${encodeURIComponent(`
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
    `)}`,
  );
}

async function loadFrontend(window: BrowserWindow): Promise<void> {
  if (process.env.FRONTEND_URL) {
    process.env.BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    await window.loadURL(frontendUrl);
    return;
  }

  if (app.isPackaged) {
    await ensurePackagedBackend();
    await window.loadFile(getFrontendIndexPath());
    return;
  }

  process.env.BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  await window.loadURL(frontendUrl);
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
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
  void loadFrontend(mainWindow).catch((error: unknown) => {
    if (mainWindow) {
      loadBackendErrorPage(mainWindow, error);
    }
  });
}


if (!app.requestSingleInstanceLock()) {
  app.quit();
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

app.on("second-instance", () => {
  if (!mainWindow) {
    return;
  }

  if (mainWindow.isMinimized()) {
    mainWindow.restore();
  }
  mainWindow.focus();
});

app.on("before-quit", () => {
  stopBackendProcess();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
