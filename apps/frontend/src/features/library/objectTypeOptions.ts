import { t } from "../../shared/text";

export interface ObjectTypeOption {
  value: string;
  labelKey: string;
  aliases?: string[];  // legacy backend values that map to the same display label
}

export interface ObjectTypeGroup {
  groupKey: string;
  options: ObjectTypeOption[];
}

const OBJECT_TYPE_GROUPS: ObjectTypeGroup[] = [
  {
    groupKey: "features.library.inbox.objectTypeGroups.video",
    options: [
      { value: "movie", labelKey: "features.library.inbox.objectTypes.movie" },
      { value: "anime", labelKey: "features.library.inbox.objectTypes.anime" },
      { value: "course", labelKey: "features.library.inbox.objectTypes.course" },
      { value: "video_collection", labelKey: "features.library.inbox.objectTypes.video_collection" },
      { value: "clip", labelKey: "features.library.inbox.objectTypes.clip", aliases: ["clip_set"] },
      { value: "movie_collection", labelKey: "features.library.inbox.objectTypes.movie_collection" },
    ],
  },
  {
    groupKey: "features.library.inbox.objectTypeGroups.image",
    options: [
      { value: "imgset", labelKey: "features.library.inbox.objectTypes.imgset", aliases: ["photo_event", "web_image_set"] },
      { value: "comic", labelKey: "features.library.inbox.objectTypes.comic" },
    ],
  },
  {
    groupKey: "features.library.inbox.objectTypeGroups.app",
    options: [
      { value: "software", labelKey: "features.library.inbox.objectTypes.software" },
      { value: "game", labelKey: "features.library.inbox.objectTypes.game" },
    ],
  },
  {
    groupKey: "features.library.inbox.objectTypeGroups.document",
    options: [
      { value: "docset", labelKey: "features.library.inbox.objectTypes.docset" },
    ],
  },
  {
    groupKey: "features.library.inbox.objectTypeGroups.audio",
    options: [
      { value: "audio", labelKey: "features.library.inbox.objectTypes.audio" },
    ],
  },
  {
    groupKey: "features.library.inbox.objectTypeGroups.asset",
    options: [
      { value: "asset_pack", labelKey: "features.library.inbox.objectTypes.asset_pack" },
    ],
  },
];

// Build alias → canonical lookup
const ALIAS_TO_CANONICAL: Record<string, string> = {};
const VALUE_TO_LABEL_KEY: Record<string, string> = {};
for (const group of OBJECT_TYPE_GROUPS) {
  for (const opt of group.options) {
    VALUE_TO_LABEL_KEY[opt.value] = opt.labelKey;
    if (opt.aliases) {
      for (const alias of opt.aliases) {
        ALIAS_TO_CANONICAL[alias] = opt.value;
        VALUE_TO_LABEL_KEY[alias] = opt.labelKey;
      }
    }
  }
}

// Set of canonical values (not aliases)
const CANONICAL_VALUES: Set<string> = new Set(
  OBJECT_TYPE_GROUPS.flatMap(g => g.options.map(o => o.value))
);

export function getObjectTypeGroups(): ObjectTypeGroup[] {
  return OBJECT_TYPE_GROUPS;
}

export function objectTypeLabel(value: string): string {
  const key = VALUE_TO_LABEL_KEY[value] || `features.library.inbox.objectTypes.${value}`;
  return t(key as Parameters<typeof t>[0]) || value;
}

export function canonicalValue(value: string): string {
  return ALIAS_TO_CANONICAL[value] || value;
}

export function isCanonicalValue(value: string): boolean {
  return CANONICAL_VALUES.has(value);
}

export function isAliasValue(value: string): boolean {
  return value in ALIAS_TO_CANONICAL;
}

export function isValidObjectType(value: string): boolean {
  return value in VALUE_TO_LABEL_KEY;
}
