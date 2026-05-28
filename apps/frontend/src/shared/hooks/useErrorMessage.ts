const ERROR_MESSAGES: Record<string, string> = {
  SCAN_ALREADY_RUNNING: "A scan is already running for this source.",
  INVALID_SOURCE_PATH: "The provided path is invalid or does not exist.",
  SOURCE_ALREADY_EXISTS: "A source with this path already exists.",
  SOURCE_ROOT_OVERLAP: "This path overlaps with an existing source root.",
  TAG_NOT_FOUND: "The requested tag could not be found.",
  FILE_NOT_FOUND: "The requested file could not be found.",
};

export function useErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    const code = (error as { code?: string }).code;
    if (code && ERROR_MESSAGES[code]) return ERROR_MESSAGES[code];
    return error.message;
  }
  return String(error ?? "An unknown error occurred");
}
