export const shell = {
  sidebar: {
    eyebrow: "Local-first asset workbench",
    title: "Asset Workbench",
    expand: "Expand sidebar",
    collapse: "Collapse sidebar",
  },
  topbar: {
    eyebrow: "Windows Local Asset Workbench",
    fallbackTitle: "Workbench",
    pages: {
      home: "Home",
      onboarding: "Onboarding",
      search: "Search",
      files: "Files",
      books: "Books",
      software: "Software",
      media: "Media Library",
      games: "Games",
      recent: "Recent Imports",
      tags: "Tags",
      collections: "Collections",
      settings: "Settings",
    },
    backend: {
      connected: "Connected",
      disconnected: "Disconnected",
    },
    details: {
      show: "Show details",
      hide: "Hide details",
    },
  },
  desktopTitleBar: {
    windowTitle: "Asset Workbench window title",
    appTitle: "Asset Workbench",
    minimize: "Minimize window",
    maximize: "Maximize window",
    restore: "Restore window",
    close: "Close window",
  },
} as const;
