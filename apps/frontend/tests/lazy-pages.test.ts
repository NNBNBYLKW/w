import { describe, expect, it } from "vitest";

const lazyPageImports = [
  ["BrowseV2Page", () => import("../src/pages/browse-v2/BrowseV2Page")],
  ["LibraryPage", () => import("../src/pages/library/LibraryPage")],
  ["SearchPage", () => import("../src/pages/search/SearchPage")],
  ["SettingsPage", () => import("../src/pages/settings/SettingsPage")],
] as const;

describe("lazy route pages", () => {
  it.each(lazyPageImports)("%s exposes a default export for React.lazy", async (_name, loadPage) => {
    const pageModule = await loadPage();

    expect(pageModule.default).toBeTypeOf("function");
  });
});
