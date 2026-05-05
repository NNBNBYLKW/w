export const pages = {
  home: {
    eyebrow: "Lightweight overview",
    title: "Home",
    description:
      "Use this lightweight overview page as the main entry to system status, source coverage, and the current indexed-file flows.",
  },
  onboarding: {
    eyebrow: "Getting started",
    title: "Source setup",
    description: "Start source setup for the local-first workbench, review saved source rows, and run an initial scan.",
  },
  search: {
    eyebrow: "Search results",
    title: "Search",
    description: "Review active indexed search results by name or path with the current filters, sorting, and pagination.",
  },
  files: {
    eyebrow: "Indexed-files browse",
    title: "Files",
    description: "Browse active indexed file records by source and exact directory.",
  },
  books: {
    eyebrow: "Library subset surface",
    title: "Books",
    description:
      "Browse recognized ebook files in a focused subset surface. Selection continues into shared details and the existing open actions.",
  },
  media: {
    eyebrow: "Visual subset surface",
    title: "Media",
    description:
      "Browse indexed images and videos in a visual subset surface. Selection continues into shared details and the existing open actions.",
  },
  games: {
    eyebrow: "Library subset surface",
    title: "Games",
    description:
      "Browse recognized game-entry files in a focused subset surface. Selection continues into shared details and the existing open actions.",
  },
  software: {
    eyebrow: "Library subset surface",
    title: "Software",
    description:
      "Browse recognized software-related files in a focused subset surface. Selection continues into shared details and the existing open actions.",
  },
  recent: {
    eyebrow: "Recent retrieval family",
    title: "Recent",
    description:
      "Use recent imports, tags, and color tags as lightweight retrieval surfaces. Selection continues into shared details and the existing open actions.",
  },
  tags: {
    eyebrow: "Tag retrieval surface",
    title: "Tags",
    description:
      "Use normal tags as a retrieval surface for active indexed files. Selection continues into shared details and the existing open actions.",
  },
  collections: {
    eyebrow: "Saved retrieval surface",
    title: "Collections",
    description:
      "Use saved retrieval conditions as reusable entry points for active indexed files. Selection continues into shared details and the existing open actions.",
  },
  settings: {
    eyebrow: "Source and system entry",
    title: "Settings",
    description: "Use this lightweight page as the source and system entry for the local-first workbench.",
  },
} as const;
