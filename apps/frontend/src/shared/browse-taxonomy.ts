/** Shared browse taxonomy constants — single source of truth for sidebar and Browse v2. */

export const DOMAINS = [
  { value: "media", labelKey: "features.browseV2.domains.media" },
  { value: "documents", labelKey: "features.browseV2.domains.documents" },
  { value: "apps", labelKey: "features.browseV2.domains.apps" },
  { value: "assets", labelKey: "features.browseV2.domains.assets" },
] as const;

export type DomainValue = (typeof DOMAINS)[number]["value"];

export type CategoryItem = { value: string; labelKey: string };

export type CategoryGroup = { groupKey?: string; items: CategoryItem[] };

export const CATEGORY_TREE: Record<DomainValue, CategoryGroup[]> = {
  media: [
    {
      groupKey: "features.browseV2.categoryGroups.video",
      items: [
        { value: "movie", labelKey: "features.browseV2.categories.movie" },
        { value: "series_anime", labelKey: "features.browseV2.categories.series_anime" },
        { value: "course", labelKey: "features.browseV2.categories.course" },
        { value: "video_collection", labelKey: "features.browseV2.categories.video_collection" },
        { value: "video_clip", labelKey: "features.browseV2.categories.video_clip" },
      ],
    },
    {
      groupKey: "features.browseV2.categoryGroups.image",
      items: [
        { value: "image_album", labelKey: "features.browseV2.categories.image_album" },
        { value: "comic", labelKey: "features.browseV2.categories.comic" },
      ],
    },
    {
      groupKey: "features.browseV2.categoryGroups.audio",
      items: [
        { value: "audio", labelKey: "features.browseV2.categories.audio" },
      ],
    },
  ],
  documents: [
    { items: [{ value: "docset", labelKey: "features.browseV2.categories.docset" }] },
  ],
  apps: [
    {
      items: [
        { value: "software", labelKey: "features.browseV2.categories.software" },
        { value: "game", labelKey: "features.browseV2.categories.game" },
      ],
    },
  ],
  assets: [
    { items: [{ value: "asset_pack", labelKey: "features.browseV2.categories.asset_pack" }] },
  ],
};
