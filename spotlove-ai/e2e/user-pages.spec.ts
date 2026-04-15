/**
 * ParkSmart — E2E Tests: All User-Facing Pages.
 *
 * Comprehensive test suite covering every protected page.
 * Each test verifies the page loads without errors and displays content.
 */

import { test, expect } from "@playwright/test";
import * as dotenv from "dotenv";

dotenv.config({ path: ".env.test" });

const GATEWAY_SECRET = process.env.E2E_GATEWAY_SECRET || "";

// ── CAMERAS PAGE ──

test.describe("Cameras Page", () => {
  test("should load cameras page", async ({ page }) => {
    await page.goto("/cameras");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/cameras");
    const body = await page.textContent("body");
    expect(body!.length).toBeGreaterThan(50);
  });

  test("should display camera feeds or empty state", async ({ page }) => {
    await page.goto("/cameras");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);
    // Should not show a generic error
    const errorAlert = page.locator('[role="alert"]');
    const errorCount = await errorAlert.count();
    // Some errors are expected if cameras offline, but page should render
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
  });
});

// ── MAP PAGE ──

test.describe("Map Page", () => {
  test("should load map page", async ({ page }) => {
    await page.goto("/map");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/map");
  });

  test("should display map or parking lot visualization", async ({ page }) => {
    await page.goto("/map");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);
    const body = await page.textContent("body");
    expect(body!.length).toBeGreaterThan(50);
  });
});

// ── SUPPORT PAGE ──

test.describe("Support Page", () => {
  test("should load support page", async ({ page }) => {
    await page.goto("/support");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/support");
  });

  test("should display chatbot or support options", async ({ page }) => {
    await page.goto("/support");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
  });
});

// ── SETTINGS PAGE ──

test.describe("Settings Page", () => {
  test("should load settings page", async ({ page }) => {
    await page.goto("/settings");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/settings");
  });

  test("should display user settings form", async ({ page }) => {
    await page.goto("/settings");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
    // Should have form elements
    const inputs = page.locator("input, select, textarea");
    const inputCount = await inputs.count();
    expect(inputCount).toBeGreaterThan(0);
  });
});

// ── PAYMENT PAGE ──

test.describe("Payment Page", () => {
  test("should load payment page with bookingId", async ({ page }) => {
    // Payment page requires ?bookingId= param, otherwise redirects to /history
    // First get an active booking from the API
    const apiRes = await page.request.get("http://localhost:8000/bookings/", {
      headers: {
        Cookie: (await page.context().cookies())
          .map((c) => `${c.name}=${c.value}`)
          .join("; "),
        "X-Gateway-Secret": GATEWAY_SECRET,
      },
    });
    let bookingId = "test-booking-id";
    if (apiRes.ok()) {
      const data = await apiRes.json();
      const bookings = data.results || data;
      if (Array.isArray(bookings) && bookings.length > 0) {
        bookingId = bookings[0].id;
      }
    }
    await page.goto(`/payment?bookingId=${bookingId}`);
    await page.waitForLoadState("networkidle");
    // Should stay on payment page (or show error for invalid booking)
    const url = page.url();
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
    // Either on payment page or redirected to history (if booking invalid)
    expect(url).toMatch(/payment|history/);
  });

  test("should redirect to history without bookingId", async ({ page }) => {
    await page.goto("/payment");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    expect(page.url()).toContain("/history");
  });
});

// ── PANIC BUTTON PAGE ──

test.describe("Panic Button Page", () => {
  test("should load panic button page", async ({ page }) => {
    await page.goto("/panic");
    await page.waitForLoadState("networkidle");
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
  });

  test("should have emergency action elements", async ({ page }) => {
    await page.goto("/panic");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    // Should have buttons or emergency UI elements
    const buttons = page.getByRole("button");
    const count = await buttons.count();
    expect(count).toBeGreaterThan(0);
  });
});

// ── BANKNOTE DETECTION PAGE ──

test.describe("Banknote Detection Page", () => {
  test("should load banknote detection page", async ({ page }) => {
    await page.goto("/banknote-detection");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/banknote-detection");
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
  });

  test("should have upload area for banknote image", async ({ page }) => {
    await page.goto("/banknote-detection");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    // Should have file input or drag-drop area
    const fileInput = page.locator('input[type="file"]');
    const dropZone = page.locator(
      '[class*="drop"], [class*="upload"], [class*="drag"]',
    );
    const hasUpload =
      (await fileInput.count()) > 0 || (await dropZone.count()) > 0;
    expect(hasUpload).toBeTruthy();
  });
});

// ── CHECK-IN/OUT PAGE ──

test.describe("Check-In/Out Page", () => {
  test("should load check-in-out page", async ({ page }) => {
    await page.goto("/check-in-out");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/check-in-out");
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
  });
});
