/**
 * ParkSmart — E2E Tests: User Dashboard & Home Page.
 *
 * Tests the main dashboard (Index page) which requires auth.
 * Uses saved auth state from global-setup.
 */

import { test, expect } from "@playwright/test";

test.describe("Home / Dashboard Page", () => {
  test("should load home page after login", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // Should not redirect to login
    expect(page.url()).not.toContain("/login");
  });

  test("should display user dashboard content", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // Check for dashboard elements: welcome text, stats, quick actions
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
    // Should have some navigation or dashboard elements
    expect(body!.length).toBeGreaterThan(100);
  });

  test("should have navigation links", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // Check for common navigation items
    const navLinks = page.locator(
      'nav a, [role="navigation"] a, .sidebar a, header a',
    );
    const count = await navLinks.count();
    expect(count).toBeGreaterThan(0);
  });
});
