/**
 * Capture screenshots of 8 main pages on parksmart.ghepdoicaulong.shop
 * Output: docs/screenshots/<page>.png (full-page 1440x900 viewport, deviceScaleFactor 1.5)
 *
 * Two sessions:
 *  - USER (user1@demo.com): index, dashboard, booking, map, history, support, payment
 *  - ADMIN (admin@example.com): admin/dashboard
 */
import { chromium, Page, BrowserContext } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const BASE = "https://parksmart.ghepdoicaulong.shop";
const USER = { email: "e2e_playwright@parksmart.com", password: "TestPass123!" };
const ADMIN = { email: "admin@parksmart.com", password: "admin1234@" };

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(__dirname, "..", "..", "docs", "screenshots");
mkdirSync(OUT_DIR, { recursive: true });

interface PageSpec {
  slug: string;
  route: string;
  waitMs?: number;
}

const USER_PAGES: PageSpec[] = [
  { slug: "01-index",            route: "/" },
  { slug: "02-user-dashboard",   route: "/" },
  { slug: "03-booking",          route: "/booking",  waitMs: 4000 },
  { slug: "04-map",              route: "/map",      waitMs: 5000 },
  { slug: "05-history",          route: "/history" },
  { slug: "06-support-chatbot",  route: "/support",  waitMs: 3500 },
  { slug: "07-payment",          route: "/payment" },
];

const ADMIN_PAGES: PageSpec[] = [
  { slug: "08-admin-dashboard",  route: "/admin/dashboard", waitMs: 4000 },
];

async function login(page: Page, user: { email: string; password: string }): Promise<boolean> {
  console.log(`→ Login as ${user.email}`);
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  try {
    await page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 15_000 });
  } catch {
    console.error("  ✗ no email input found");
    return false;
  }
  await page.fill('input[type="email"], input[name="email"]', user.email);
  await page.fill('input[type="password"], input[name="password"]', user.password);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 25_000 }).catch(() => null),
    page.click('button[type="submit"]'),
  ]);
  await page.waitForTimeout(2_000);
  const ok = !page.url().includes("/login");
  console.log(ok ? `  ✓ logged in → ${page.url()}` : `  ✗ login failed, still at ${page.url()}`);
  return ok;
}

async function capturePage(page: Page, spec: PageSpec): Promise<void> {
  const url = `${BASE}${spec.route}`;
  console.log(`→ ${spec.slug} (${url})`);
  try {
    await page.goto(url, { waitUntil: "networkidle", timeout: 25_000 });
  } catch {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 25_000 });
  }
  await page.waitForTimeout(spec.waitMs ?? 2_500);
  const out = resolve(OUT_DIR, `${spec.slug}.png`);
  await page.screenshot({ path: out, fullPage: true });
  console.log(`  ✓ ${out}`);
}

async function runSession(
  pages: PageSpec[],
  creds: { email: string; password: string }
): Promise<{ ok: number; fail: number }> {
  const browser = await chromium.launch({ headless: true });
  const context: BrowserContext = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1.5,
    locale: "vi-VN",
    timezoneId: "Asia/Ho_Chi_Minh",
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();

  let ok = 0, fail = 0;
  const ldOk = await login(page, creds);
  if (!ldOk) {
    console.error(`  → skipping pages for ${creds.email}`);
    await browser.close();
    return { ok: 0, fail: pages.length };
  }
  for (const spec of pages) {
    try {
      await capturePage(page, spec);
      ok++;
    } catch (e) {
      console.error(`  ✗ FAIL ${spec.slug}: ${(e as Error).message}`);
      fail++;
    }
  }
  await browser.close();
  return { ok, fail };
}

(async () => {
  console.log("=== USER SESSION ===");
  const u = await runSession(USER_PAGES, USER);
  console.log("=== ADMIN SESSION ===");
  const a = await runSession(ADMIN_PAGES, ADMIN);
  console.log(`\nDone. user=${u.ok}/${USER_PAGES.length} admin=${a.ok}/${ADMIN_PAGES.length}`);
})().catch((e) => {
  console.error("Fatal:", e);
  process.exit(1);
});
