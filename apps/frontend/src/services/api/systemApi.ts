type SystemStatus = {
  app: string;
  database: string;
  sources_count: number;
  tasks_count: number;
  files_count: number;
};


function getApiBaseUrl() {
  const desktopApi = (
    window as typeof window & {
      assetWorkbench?: {
        getBackendBaseUrl?: () => string;
      };
    }
  ).assetWorkbench;
  return desktopApi?.getBackendBaseUrl?.() ?? import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
}


export async function getSystemStatus(): Promise<SystemStatus> {
  const response = await fetch(`${getApiBaseUrl()}/system/status`);
  if (!response.ok) {
    throw new Error("Failed to fetch system status.");
  }
  return response.json() as Promise<SystemStatus>;
}
