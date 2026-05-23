import { t } from "../../shared/text";
import { DOMAINS, CATEGORY_TREE, type DomainValue } from "../../shared/browse-taxonomy";

export function asTextKey(key: string): Parameters<typeof t>[0] {
  return key as Parameters<typeof t>[0];
}

export function objectTypeLabel(objectType: string | null): string {
  if (!objectType) return "";
  const keyMap: Record<string, string> = {
    movie: "features.browseV2.categories.movie",
    anime: "features.browseV2.categories.series_anime",
    course: "features.browseV2.categories.course",
    video_collection: "features.browseV2.categories.video_collection",
    clip: "features.browseV2.categories.video_clip",
    clip_set: "features.browseV2.categories.video_clip",
    movie_collection: "features.browseV2.categories.video_collection",
    imgset: "features.browseV2.categories.image_album",
    photo_event: "features.browseV2.categories.image_album",
    web_image_set: "features.browseV2.categories.image_album",
    comic: "features.browseV2.categories.comic",
    audio: "features.browseV2.categories.audio",
    docset: "features.browseV2.categories.docset",
    software: "features.browseV2.categories.software",
    game: "features.browseV2.categories.game",
    asset_pack: "features.browseV2.categories.asset_pack",
  };
  const key = keyMap[objectType] || `features.library.inbox.objectTypes.${objectType}`;
  return t(asTextKey(key)) || objectType;
}

export function objectSourceLabel(source: string): string {
  return t(asTextKey(`features.browseV2.objectSource.${source}`)) || source;
}

export function storageStateLabel(storageState: string | null): string {
  if (!storageState) return "";
  return t(asTextKey(`features.browseV2.storageState.${storageState}`)) || storageState;
}

export function fileKindLabel(fileKind: string | null): string {
  if (!fileKind) return "";
  return t(asTextKey(`features.browseV2.fileKind.${fileKind}`)) || fileKind;
}

export function memberRoleLabel(role: string | null): string {
  if (!role) return "";
  const map: Record<string, string> = {
    primary: "features.browseV2.roles.primary",
    extra: "features.browseV2.roles.extra",
    subtitle: "features.browseV2.roles.subtitle",
    metadata: "features.browseV2.roles.metadata",
    artwork: "features.browseV2.roles.artwork",
    unknown_child: "features.browseV2.roles.other",
  };
  const key = map[role];
  return key ? t(asTextKey(key)) : role;
}

export function confidenceLabel(confidence: string | null): string {
  if (!confidence) return "";
  return t(asTextKey(`features.browseV2.confidence.${confidence}`)) || confidence;
}

export function formatBytes(value: number | null): string {
  if (value === null) return "";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  const formatted = new Intl.NumberFormat(undefined, {
    maximumFractionDigits: size >= 10 || unitIndex === 0 ? 0 : 1,
  }).format(size);
  return `${formatted} ${units[unitIndex]}`;
}

export function getCategoryLabel(domain: DomainValue, category: string): string {
  if (!category) {
    const domainLabel = DOMAINS.find((item) => item.value === domain)?.labelKey;
    return domainLabel ? t(asTextKey(domainLabel)) : domain;
  }
  for (const group of CATEGORY_TREE[domain]) {
    const item = group.items.find((candidate) => candidate.value === category);
    if (item) return t(asTextKey(item.labelKey));
  }
  return category;
}
