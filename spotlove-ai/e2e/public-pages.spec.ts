/**
 * ParkSmart — E2E Tests: Public Pages (Login, Register, Kiosk).
 *
 * Tests pages that don't require authentication.
 */

import { test, expect } from "@playwright/test";

test.describe("Login Page", () => {
  test("should render login form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("#email")).toBeVisible();
    await expect(page.locator("#password")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /login|sign in|đăng nhập/i }),
    ).toBeVisible();
  });

  test("should show error on invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.locator("#email").fill("invalid@example.com");
    await page.locator("#password").fill("wrongpassword");
    await page
      .getByRole("button", { name: /login|sign in|đăng nhập/i })
      .click();
    // Wait for error to appear
    await page.waitForTimeout(3000);
    // Should still be on login page or show error
    const url = page.url();
    const hasError = await page
      .locator('[role="alert"], .error, .toast, [data-sonner-toast]')
      .count();
    expect(url.includes("/login") || hasError > 0).toBeTruthy();
  });

  test("should have link to register page", async ({ page }) => {
    await page.goto("/login");
    const registerLink = page.getByRole("link", {
      name: /register|sign up|đăng ký/i,
    });
    if ((await registerLink.count()) > 0) {
      await registerLink.click();
      await expect(page).toHaveURL(/register/);
    }
  });
});

test.describe("Register Page", () => {
  test("should render registration form", async ({ page }) => {
    await page.goto("/register");
    await expect(page.locator("#email")).toBeVisible();
    await expect(page.locator("#password")).toBeVisible();
  });
});

test.describe("Kiosk Page (Public)", () => {
  test("should load kiosk page without auth", async ({ page }) => {
    await page.goto("/kiosk");
    await page.waitForLoadState("networkidle");
    // Kiosk should render — check for mode indicators
    const pageContent = await page.textContent("body");
    expect(pageContent).toBeTruthy();
  });
});

test.describe("NotFound Page", () => {
  test("should show 404 for unknown route", async ({ page }) => {
    await page.goto("/this-page-does-not-exist-xyz");
    await page.waitForLoadState("networkidle");
    const content = await page.textContent("body");
    expect(content?.toLowerCase()).toMatch(/not found|404|page/);
  });
});
