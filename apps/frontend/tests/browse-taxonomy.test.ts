import { describe, it, expect } from "vitest";
import { DOMAINS, CATEGORY_TREE } from "../src/shared/browse-taxonomy";

describe("browse taxonomy constants", () => {
  it("has all four domains", () => {
    const values = DOMAINS.map((d) => d.value);
    expect(values).toEqual(["media", "documents", "apps", "assets"]);
  });

  it("every domain has a labelKey", () => {
    for (const d of DOMAINS) {
      expect(d.labelKey).toMatch(/^features\.browseV2\.domains\./);
    }
  });

  it("media domain has video, image, and audio groups", () => {
    const media = CATEGORY_TREE.media;
    const groupKeys = media.map((g) => g.groupKey).filter(Boolean);
    expect(groupKeys).toContain("features.browseV2.categoryGroups.video");
    expect(groupKeys).toContain("features.browseV2.categoryGroups.image");
    expect(groupKeys).toContain("features.browseV2.categoryGroups.audio");
  });

  it("media domain has 8 subcategories", () => {
    const media = CATEGORY_TREE.media;
    const allItems = media.flatMap((g) => g.items);
    expect(allItems).toHaveLength(8);
  });

  it("apps domain has software and game", () => {
    const apps = CATEGORY_TREE.apps;
    const allItems = apps.flatMap((g) => g.items);
    const values = allItems.map((i) => i.value).sort();
    expect(values).toEqual(["game", "software"]);
  });

  it("every category item has value and labelKey", () => {
    const domains = Object.keys(CATEGORY_TREE) as Array<keyof typeof CATEGORY_TREE>;
    for (const domain of domains) {
      for (const group of CATEGORY_TREE[domain]) {
        for (const item of group.items) {
          expect(item.value).toBeTruthy();
          expect(item.labelKey).toMatch(/^features\.browseV2\./);
        }
      }
    }
  });

  it("all domain values are unique", () => {
    const values = DOMAINS.map((d) => d.value);
    expect(new Set(values).size).toBe(values.length);
  });
});
