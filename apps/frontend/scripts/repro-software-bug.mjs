// Reproduce white screen when clicking library object
import { chromium } from "playwright";

const BASE = "http://127.0.0.1:5173";

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const consoleErrors = [];
  const pageErrors = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push(msg.text());
      console.log(`[CONSOLE ERROR] ${msg.text().substring(0, 200)}`);
    }
    if (msg.type() === "warning") {
      console.log(`[CONSOLE WARN] ${msg.text().substring(0, 150)}`);
    }
  });
  page.on("pageerror", (err) => {
    pageErrors.push(err.message);
    console.log(`[PAGE ERROR] ${err.message}`);
  });

  try {
    // Navigate to Library Objects
    console.log("Navigating to /library?tab=objects...");
    await page.goto(`${BASE}/library?tab=objects`, { waitUntil: "networkidle", timeout: 15000 });
    await page.waitForTimeout(1500);

    // Check for white screen
    const rootChildren = await page.evaluate(() => {
      const root = document.getElementById("root");
      return root ? root.children.length : -1;
    });
    console.log(`Root children: ${rootChildren}`);

    // Get page text content
    const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 300));
    console.log(`Body text preview: ${bodyText}`);

    // Find object rows
    const objectRows = page.locator(".library-object-row, .compact-library-table__row, .asset-icon-card");
    const rowCount = await objectRows.count();
    console.log(`Found ${rowCount} object rows/cards`);

    if (rowCount > 0) {
      // Get the text of first few rows
      for (let i = 0; i < Math.min(rowCount, 5); i++) {
        const text = await objectRows.nth(i).innerText();
        console.log(`Row ${i}: ${text.substring(0, 80)}`);
      }

      // Click the first row
      console.log("\nClicking first object row...");
      await objectRows.first().click();
      await page.waitForTimeout(1500);

      // Check if page is still alive
      const stillAlive = await page.evaluate(() => {
        const root = document.getElementById("root");
        return root && root.children.length > 0;
      });
      console.log(`Page alive after click: ${stillAlive}`);

      // Check for white screen
      const bodyTextAfter = await page.evaluate(() => document.body.innerText.substring(0, 300));
      console.log(`Body text after click: ${bodyTextAfter}`);

      // Check what URL we're on now
      console.log(`Current URL: ${page.url()}`);

      // Check for visible error text
      const hasErrorText = await page.evaluate(() => {
        return document.body.innerText.includes("Error:") ||
               document.body.innerText.includes("Uncaught") ||
               document.body.innerText.includes("TypeError") ||
               document.body.innerText.includes("undefined");
      });
      console.log(`Error text visible: ${hasErrorText}`);

      // Check DetailsPanel
      const detailsVisible = await page.locator(".details-panel, .details-panel-card").isVisible();
      console.log(`DetailsPanel visible: ${detailsVisible}`);

      // Take screenshot
      await page.screenshot({ path: "../../docs/_wip/frontend-acceptance/screenshots/bug-repro-after-click.png" });
    } else {
      console.log("No object rows found - page might be empty");
      await page.screenshot({ path: "../../docs/_wip/frontend-acceptance/screenshots/bug-repro-empty.png" });
    }
  } catch (e) {
    console.log(`FATAL: ${e.message}`);
    try {
      await page.screenshot({ path: "../../docs/_wip/frontend-acceptance/screenshots/bug-repro-crash.png" });
    } catch {}
  }

  console.log(`\n--- Summary ---`);
  console.log(`Console errors: ${consoleErrors.length}`);
  for (const e of consoleErrors) {
    console.log(`  ${e.substring(0, 200)}`);
  }
  console.log(`Page errors: ${pageErrors.length}`);
  for (const e of pageErrors) {
    console.log(`  ${e}`);
  }

  await context.close();
  await browser.close();
}

main().catch((e) => console.error("Script error:", e.message));
