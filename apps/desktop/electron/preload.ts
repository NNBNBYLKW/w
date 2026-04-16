import fs from "node:fs";
import path from "node:path";

import { contextBridge, shell } from "electron";


const backendBaseUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";


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


function deriveContainingFolderPath(filePath: string): string | null {
  const normalizedPath = normalizeInputPath(filePath);
  if (!normalizedPath) {
    return null;
  }

  const parentDirectory = path.win32.dirname(normalizedPath);
  if (!parentDirectory || parentDirectory === "." || parentDirectory === normalizedPath) {
    return null;
  }

  return parentDirectory;
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
  const parentDirectory = deriveContainingFolderPath(filePath);
  if (!parentDirectory) {
    return {
      ok: false,
      reason: "A containing folder could not be derived from this file path.",
    };
  }

  if (!fs.existsSync(parentDirectory)) {
    return {
      ok: false,
      reason: "The containing folder does not exist.",
    };
  }

  try {
    if (!fs.statSync(parentDirectory).isDirectory()) {
      return {
        ok: false,
        reason: "The containing folder does not exist.",
      };
    }
  } catch {
    return {
      ok: false,
      reason: "The containing folder could not be verified.",
    };
  }

  const errorMessage = await shell.openPath(parentDirectory);
  if (errorMessage) {
    return {
      ok: false,
      reason: errorMessage,
    };
  }

  return { ok: true };
}


contextBridge.exposeInMainWorld("assetWorkbench", {
  getBackendBaseUrl: () => backendBaseUrl,
  selectFolder: async () => null,
  openFile,
  openContainingFolder,
});
