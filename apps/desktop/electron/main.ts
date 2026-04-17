import path from "node:path";

import { app, BrowserWindow } from "electron";


const frontendUrl = process.env.FRONTEND_URL ?? "http://127.0.0.1:5173";


function createMainWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 720,
    backgroundColor: "#0d1117",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      // The preload bridge uses node:fs and node:path to implement desktop open
      // actions, so it must run outside the sandboxed preload environment.
      sandbox: false,
    },
  });

  void window.loadURL(frontendUrl);
}


app.whenReady().then(() => {
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
