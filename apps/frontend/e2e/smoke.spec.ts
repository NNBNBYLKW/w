import { test, expect } from "@playwright/test";

test("homepage loads with sidebar", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("nav, .app-sidebar").first()).toBeVisible({ timeout: 10000 });
});

test("can navigate to settings", async ({ page }) => {
  await page.goto("/");
  await page.click("text=Settings");
  await expect(page.locator("text=Theme, text=Appearance, text=System").first()).toBeVisible({ timeout: 5000 });
});

test("search page has input field", async ({ page }) => {
  await page.goto("/search");
  await expect(page.locator("input[placeholder*='Search'], input[placeholder*='搜索']")).toBeVisible();
});

test("library page loads with tabs", async ({ page }) => {
  await page.goto("/library");
  await expect(page.locator("text=Overview, text=Sources, text=Roots").first()).toBeVisible({ timeout: 5000 });
});
