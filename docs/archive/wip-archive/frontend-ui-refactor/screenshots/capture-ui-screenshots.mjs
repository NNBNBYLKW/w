import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = __dirname;
const BASE_URL = "http://127.0.0.1:5173";
const VIEWPORT = { width: 1440, height: 900 };

async function shoot(page, path, name, notes) {
  await page.goto(`${BASE_URL}${path}`, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1500);
  const file = join(SCREENSHOT_DIR, name);
  await page.screenshot({ path: file, fullPage: false });
  console.log(`  ${name}: ${notes}`);
}

async function main() {
  mkdirSync(SCREENSHOT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    colorScheme: "dark",
  });

  // Set dark theme + locale to zh-CN
  const page = await context.newPage();
  await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem("workbench-theme", "dark");
  });

  console.log("📸 Capturing screenshots (backend: not running — empty states)...\n");

  await shoot(page, "/home", "01_home.png", "Home page");
  await shoot(page, "/settings", "11_settings.png", "Settings page");
  await shoot(page, "/tools", "10_tools.png", "Tools page");
  await shoot(page, "/library?tab=roots", "03_library_managed_roots.png", "Managed Roots tab");
  await shoot(page, "/library?tab=pending", "05_library_pending.png", "Pending tab");
  await shoot(page, "/library?tab=plans", "06_library_plan_detail.png", "Organize Plans tab");
  await shoot(page, "/recent", "07_recent.png", "Recent page");
  await shoot(page, "/tags", "08_tags.png", "Tags page");
  await shoot(page, "/collections", "09_collections.png", "Collections page");

  // Verify key CSS classes in DOM
  console.log("\n🔍 Checking key CSS classes in DOM...");
  await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(1000);
  const classes = [
    "action-button", "kv-row", "library-suggestion-card",
    "library-reconcile-section", "retrieval-segment", "tool-card", "settings-section"
  ];
  for (const cls of classes) {
    const count = await page.evaluate((c) => document.querySelectorAll(`.${c}`).length, cls);
    console.log(`  .${cls}: ${count} elements`);
  }

  await browser.close();
  console.log("\n✅ Screenshots saved to:", SCREENSHOT_DIR);
}

main().catch((err) => {
  console.error("❌ Screenshot error:", err.message);
  process.exit(1);
});
