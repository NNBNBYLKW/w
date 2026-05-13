import type { OrganizeSuggestionItemVM } from "../../../entities/library/types";

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

export function formatBytes(value: number | null): string {
  if (value === null) return "—";
  if (value < 1024) return `${value.toLocaleString()} bytes`;
  const units = ["KB", "MB", "GB", "TB"];
  let current = value / 1024;
  let unitIndex = 0;
  while (current >= 1024 && unitIndex < units.length - 1) {
    current /= 1024;
    unitIndex += 1;
  }
  return `${current.toFixed(current >= 10 ? 0 : 1)} ${units[unitIndex]}`;
}

export function formatSuggestionPayloadSummary(suggestion: OrganizeSuggestionItemVM): string {
  try {
    const payload = JSON.parse(suggestion.payload_json) as Record<string, unknown>;
    if (suggestion.suggestion_type === "title") return String(payload.title ?? "");
    if (suggestion.suggestion_type === "object_type") return String(payload.object_type ?? "");
    if (suggestion.suggestion_type === "template_key") return String(payload.template_key ?? "");
    if (suggestion.suggestion_type === "tags") {
      return Array.isArray(payload.tags) ? payload.tags.map(String).join(", ") || "—" : "—";
    }
    if (suggestion.suggestion_type === "asset_yaml") {
      return [`type: ${payload.type ?? "—"}`, `title: ${payload.title ?? "—"}`, `year: ${payload.year ?? "—"}`].join(" · ");
    }
    return suggestion.payload_json.slice(0, 160);
  } catch {
    return suggestion.payload_json.slice(0, 160);
  }
}

export function normalizeObjectTypeLabel(value: string): string {
  return value.replace(/_/g, " ").toUpperCase();
}
