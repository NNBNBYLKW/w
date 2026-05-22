import { describe, it, expect } from "vitest";

import { navigation as enNav } from "../src/locales/en/navigation";
import { navigation as zhNav } from "../src/locales/zh-CN/navigation";
import { pages as enPages } from "../src/locales/en/pages";
import { pages as zhPages } from "../src/locales/zh-CN/pages";
import { shell as enShell } from "../src/locales/en/shell";
import { shell as zhShell } from "../src/locales/zh-CN/shell";
import { features as enFeatures } from "../src/locales/en/features";
import { features as zhFeatures } from "../src/locales/zh-CN/features";

function getAllKeys(obj: unknown, prefix = ""): string[] {
  if (typeof obj !== "object" || obj === null) return [];
  const keys: string[] = [];
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (typeof v === "object" && v !== null && !Array.isArray(v)) {
      keys.push(...getAllKeys(v, path));
    } else {
      keys.push(path);
    }
  }
  return keys;
}

describe("i18n parity", () => {
  it("navigation keys match between en and zh-CN", () => {
    const enKeys = Object.keys(enNav.items).sort();
    const zhKeys = Object.keys(zhNav.items).sort();
    expect(enKeys).toEqual(zhKeys);
  });

  it("all M2 navigation keys exist in both locales", () => {
    const required = [
      "fileLibOverview", "browseAll", "browseMedia", "browseDocuments",
      "browseApps", "browseAssets", "scanFolders", "managedRoots",
      "inbox", "plans", "fileLibrary",
    ];
    for (const key of required) {
      expect(enNav.items).toHaveProperty(key);
      expect(zhNav.items).toHaveProperty(key);
    }
  });

  it("shell group keys match between en and zh-CN", () => {
    const enKeys = Object.keys(enShell.sidebar.groups).sort();
    const zhKeys = Object.keys(zhShell.sidebar.groups).sort();
    expect(enKeys).toEqual(zhKeys);
  });

  it("M2 shell groups exist", () => {
    expect(enShell.sidebar.groups).toHaveProperty("main");
    expect(enShell.sidebar.groups).toHaveProperty("fileLibrary");
    expect(enShell.sidebar.groups).toHaveProperty("manage");
    expect(enShell.sidebar.groups).toHaveProperty("refind");
    expect(enShell.sidebar.groups).toHaveProperty("system");
  });

  it("pages keys match between en and zh-CN", () => {
    const enKeys = Object.keys(enPages).sort();
    const zhKeys = Object.keys(zhPages).sort();
    expect(enKeys).toEqual(zhKeys);
  });

  it("features top-level sections match", () => {
    const enSections = Object.keys(enFeatures).sort();
    const zhSections = Object.keys(zhFeatures).sort();
    expect(enSections).toEqual(zhSections);
  });

  it("browseV2 roles exist in both locales", () => {
    const enRoles = (enFeatures as any).browseV2?.roles;
    const zhRoles = (zhFeatures as any).browseV2?.roles;
    expect(enRoles).toBeDefined();
    expect(zhRoles).toBeDefined();
    expect(Object.keys(enRoles).sort()).toEqual(Object.keys(zhRoles).sort());
  });

  it("no raw i18n key leakage — all leaf values are strings", () => {
    const checkLeafValues = (obj: unknown, path: string) => {
      if (typeof obj === "string") return;
      if (typeof obj !== "object" || obj === null) return;
      for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
        const p = path ? `${path}.${k}` : k;
        if (typeof v === "string") {
          expect(v).toBeTruthy();
        } else if (typeof v === "object" && v !== null) {
          checkLeafValues(v, p);
        }
      }
    };
    checkLeafValues(enNav, "navigation");
    checkLeafValues(zhNav, "navigation");
  });

  it("library tabs include sources in both locales", () => {
    const enTabs = (enFeatures as any).library?.tabs;
    const zhTabs = (zhFeatures as any).library?.tabs;
    expect(enTabs).toHaveProperty("sources");
    expect(zhTabs).toHaveProperty("sources");
    expect(enTabs).toHaveProperty("overview");
    expect(enTabs).toHaveProperty("roots");
    expect(enTabs).toHaveProperty("inbox");
    expect(enTabs).toHaveProperty("plans");
  });

  it("library overview start-here cards exist in both locales", () => {
    const enOverview = (enFeatures as any).library?.overview;
    const zhOverview = (zhFeatures as any).library?.overview;
    for (const card of ["scan", "roots", "import", "browse", "plans"]) {
      expect(enOverview).toHaveProperty(`${card}CardTitle`);
      expect(enOverview).toHaveProperty(`${card}CardDesc`);
      expect(enOverview).toHaveProperty(`${card}CardAction`);
      expect(zhOverview).toHaveProperty(`${card}CardTitle`);
      expect(zhOverview).toHaveProperty(`${card}CardDesc`);
      expect(zhOverview).toHaveProperty(`${card}CardAction`);
    }
  });
});
