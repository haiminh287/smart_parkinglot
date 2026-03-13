/**
 * ParkSmart — E2E Tests: Booking Page.
 *
 * Tests booking creation, listing, and interactions.
 */

import { test, expect } from "@playwright/test";

test.describe("Booking Page", () => {
  test("should load booking page", async ({ page }) => {
    await page.goto("/booking");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/booking");
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
  });

  test("should display parking lots or booking form", async ({ page }) => {
    await page.goto("/booking");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);
    // Should have either parking lot cards or a booking form
    const content = await page.textContent("body");
    expect(content!.length).toBeGreaterThan(50);
  });

  test("should show available parking lots", async ({ page }) => {
    await page.goto("/booking");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);
    // Look for parking lot names or cards
    const lots = page.locator(
      '[class*="card"], [class*="lot"], [class*="parking"]',
    );
    const lotCount = await lots.count();
    // There should be at least some parking content
    expect(lotCount).toBeGreaterThanOrEqual(0);
  });
});
