import type { ColorTagValue, FileRatingValue, FileStatusValue, ManualPlacementValue, PlacementValue } from "../../../entities/file/types";
import { t } from "../../../shared/text";

export function formatTimestamp(value: string | null): string {
  return value ? new Date(value).toLocaleString() : t("details.values.unavailable");
}

export function formatBytes(value: number | null): string {
  return value === null ? t("details.values.unavailable") : `${value.toLocaleString()} bytes`;
}

export function formatMetadataValue(value: number | null, suffix?: string): string {
  if (value === null) {
    return t("details.values.unavailable");
  }
  return suffix ? `${value.toLocaleString()} ${suffix}` : value.toLocaleString();
}

export function formatDurationMs(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return "—";
  }
  const totalSeconds = Math.round(value / 1000);
  if (totalSeconds <= 0) {
    return "—";
  }
  if (totalSeconds < 60) {
    return `${totalSeconds}秒`;
  }
  const totalMinutes = Math.floor(totalSeconds / 60);
  if (totalMinutes < 60) {
    return `${totalMinutes}分钟${totalSeconds % 60}秒`;
  }
  return `${Math.floor(totalMinutes / 60)}小时${totalMinutes % 60}分`;
}

export function formatDimensions(width: number | null, height: number | null): string {
  if (width === null && height === null) {
    return t("details.values.unavailable");
  }
  const widthLabel = width === null ? "?" : width.toLocaleString();
  const heightLabel = height === null ? "?" : height.toLocaleString();
  return `${widthLabel} × ${heightLabel} px`;
}

export const COLOR_TAG_OPTIONS: ColorTagValue[] = ["red", "yellow", "green", "blue", "purple"];
export const GAME_STATUS_OPTIONS: FileStatusValue[] = ["playing", "completed", "shelved"];
export const PLACEMENT_OPTIONS = [
  { labelKey: "details.placement.options.auto", value: "auto" },
  { labelKey: "details.placement.options.media", value: "media" },
  { labelKey: "details.placement.options.books", value: "books" },
  { labelKey: "details.placement.options.games", value: "games" },
  { labelKey: "details.placement.options.software", value: "software" },
  { labelKey: "details.placement.options.filesOnly", value: "files_only" },
] as const satisfies ReadonlyArray<{ labelKey: Parameters<typeof t>[0]; value: ManualPlacementValue | "auto" }>;

export function formatStatusLabel(value: FileStatusValue): string {
  return value === "playing" ? "Playing" : value === "completed" ? "Completed" : "Shelved";
}

export const DOCUMENT_DETAIL_EXTENSIONS = ["azw3", "csv", "doc", "docx", "epub", "md", "mobi", "odp", "ods", "odt", "pdf", "ppt", "pptx", "rtf", "txt", "xls", "xlsx"] as const;

export function inferBookFormat(name: string, path: string): string | null {
  const candidate = `${name} ${path}`.toLowerCase();
  const matchedExtension = DOCUMENT_DETAIL_EXTENSIONS.find((extension) => candidate.includes(`.${extension}`));
  return matchedExtension ?? null;
}

export function buildBookDisplayTitle(name: string): string {
  const withoutExtension = name.replace(/\.(azw3|csv|doc|docx|epub|md|mobi|odp|ods|odt|pdf|ppt|pptx|rtf|txt|xls|xlsx)$/i, "");
  const normalized = withoutExtension.replace(/_/g, " ").replace(/\s+/g, " ").trim();
  return normalized || name;
}

export function formatBookFormatLabel(value: string): string {
  return value.toUpperCase();
}

export function inferSoftwareFormat(name: string, path: string): "exe" | "msi" | "zip" | null {
  const candidate = `${name} ${path}`.toLowerCase();
  if (candidate.includes(".exe")) {
    return "exe";
  }
  if (candidate.includes(".msi")) {
    return "msi";
  }
  if (candidate.includes(".zip")) {
    return "zip";
  }
  return null;
}

export function buildSoftwareDisplayTitle(name: string): string {
  const withoutExtension = name.replace(/\.(exe|msi|zip)$/i, "");
  const normalized = withoutExtension.replace(/_/g, " ").replace(/\s+/g, " ").trim();
  return normalized || name;
}

export function formatSoftwareFormatLabel(value: "exe" | "msi" | "zip"): string {
  return value.toUpperCase();
}

export function buildSoftwareEntryTypeLabel(value: "exe" | "msi" | "zip"): string {
  if (value === "exe") {
    return "Executable entry";
  }
  if (value === "msi") {
    return "Installer package";
  }
  return "Archive package";
}

export function inferGameEntry(name: string, path: string): boolean {
  const candidate = `${name} ${path}`.toLowerCase();
  if (candidate.includes(".lnk")) {
    return true;
  }
  if (!candidate.includes(".exe")) {
    return false;
  }
  return [
    "\\games\\",
    "\\game\\",
    "\\steam\\",
    "\\steamapps\\",
    "\\gog\\",
    "\\epic games\\",
    "\\itch\\",
    "\\riot games\\",
    "\\blizzard\\",
    "\\battle.net\\",
    "\\ubisoft\\",
    "\\rockstar games\\",
    "\\ea games\\",
  ].some((hint) => candidate.includes(hint));
}

export function formatFavoriteLabel(isFavorite: boolean): string {
  return isFavorite ? t("details.values.markedFavorite") : t("details.values.notMarked");
}

export function formatRatingLabel(value: FileRatingValue | null): string {
  return value === null ? t("details.values.none") : `${value} / 5`;
}

export function formatPlacementLabel(value: PlacementValue | ManualPlacementValue | null): string {
  if (value === null) {
    return t("details.placement.options.auto");
  }
  if (value === "media") {
    return t("details.placement.options.media");
  }
  if (value === "books") {
    return t("details.placement.options.books");
  }
  if (value === "games") {
    return t("details.placement.options.games");
  }
  if (value === "software") {
    return t("details.placement.options.software");
  }
  if (value === "files_only") {
    return t("details.placement.options.filesOnly");
  }
  return t("details.placement.options.none");
}
