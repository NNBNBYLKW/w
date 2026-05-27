import { getApiBaseUrl, parseResponse } from "./client";

type SystemStatus = {
  app: string;
  database: string;
  sources_count: number;
  tasks_count: number;
  files_count: number;
};

export type RuntimeDiagnostics = {
  process_id: number;
  process_start_time: number;
  sys_executable: string;
  cwd: string;
  data_dir: string;
  database_path: string;
  database_url: string;
  pypdfium2_import: string;
  pypdfium2_version: string | null;
  pypdfium2_error: string | null;
  packaged_backend: boolean;
};


export async function getSystemStatus(): Promise<SystemStatus> {
  const response = await fetch(`${getApiBaseUrl()}/system/status`);
  if (!response.ok) {
    throw new Error("Failed to fetch system status.");
  }
  return response.json() as Promise<SystemStatus>;
}

export async function getRuntimeDiagnostics(): Promise<RuntimeDiagnostics> {
  const response = await fetch(`${getApiBaseUrl()}/debug/runtime`);
  return parseResponse<RuntimeDiagnostics>(response);
}

export async function clearThumbnailCache(): Promise<{ message: string }> {
  const response = await fetch(`${getApiBaseUrl()}/debug/thumbnails/clear-cache`, {
    method: "POST",
  });
  return parseResponse<{ message: string }>(response);
}
