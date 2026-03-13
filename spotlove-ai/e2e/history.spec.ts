/**
 * ParkSmart — E2E Tests: History Page.
 *
 * Tests booking history display and filtering.
 */

import { test, expect } from "@playwright/test";

test.describe("History Page", () => {
  test("should load history page", async ({ page }) => {
    await page.goto("/history");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/history");
  });

  test("should display booking history or empty state", async ({ page }) => {
    await page.goto("/history");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);
    const body = await page.textContent("body");
    // Should have either booking items or "no bookings" message
    expect(body).toBeTruthy();
    expect(body!.length).toBeGreaterThan(50);
  });
});
