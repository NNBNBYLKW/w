export function getApiBaseUrl(): string {
  const bridge = (window as { assetWorkbench?: { getBackendBaseUrl?: () => string } }).assetWorkbench;
  if (bridge?.getBackendBaseUrl) {
    const url = bridge.getBackendBaseUrl();
    if (url) return url;
  }
  const envUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (envUrl) return envUrl;
  return "http://127.0.0.1:8000";
}

type ErrorConstructor = new (message: string, code: string | null) => Error;

export async function parseResponse<T>(response: Response, ErrorClass?: ErrorConstructor): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({} as Record<string, unknown>));
    const message = (body.detail as string) ?? (body.message as string) ?? `HTTP ${response.status}`;
    const code = (body.code as string) ?? null;
    if (ErrorClass) throw new ErrorClass(message, code);
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
