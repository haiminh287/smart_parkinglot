/**
 * ParkSmart — Playwright Global Setup.
 *
 * Registers a test user + admin user, logs in both, and saves auth state
 * so individual tests don't need to re-login.
 */

import { test as setup, expect } from "@playwright/test";
import type { APIRequestContext } from "@playwright/test";
import fs from "fs";
import path from "path";

const AUTH_DIR = path.resolve("e2e", ".auth");

const GATEWAY_URL = "http://localhost:8000";
const GATEWAY_SECRET = "gateway-internal-secret-key";

const USER_CREDENTIALS = {
  email: "e2e_playwright@parksmart.com",
  username: "e2e_playwright",
  password: "TestPass123!",
};

const ADMIN_CREDENTIALS = {
  email: "admin@parksmart.com",
  username: "admin",
  password: "admin1234@",
};

interface AuthCookie {
  name: string;
  value: string;
}

async function ensureTestUser(request: APIRequestContext) {
  // Try registering. Ignore 400 (already exists).
  const res = await request.post(`${GATEWAY_URL}/auth/register/`, {
    data: {
      email: USER_CREDENTIALS.email,
      username: USER_CREDENTIALS.username,
      password: USER_CREDENTIALS.password,
      password_confirm: USER_CREDENTIALS.password,
    },
  });
  if (res.status() === 201) {
    console.log("✅ Test user registered");
  } else {
    console.log(
      `ℹ️ Test user registration: ${res.status()} (likely already exists)`,
    );
  }
}

async function ensureTestDataForUser(
  request: APIRequestContext,
  cookies: AuthCookie[],
) {
  const headers: Record<string, string> = {
    "X-Gateway-Secret": GATEWAY_SECRET,
  };
  // Build cookie header from cookies array
  const cookieStr = cookies.map((c) => `${c.name}=${c.value}`).join("; ");
  if (cookieStr) headers["Cookie"] = cookieStr;

  // Get CSRF token
  const csrfCookie = cookies.find((c) => c.name === "csrftoken");
  if (csrfCookie) headers["X-CSRFToken"] = csrfCookie.value;

  // 1. Register a vehicle
  const vehicleRes = await request.post(`${GATEWAY_URL}/vehicles/`, {
    headers: { ...headers, "Content-Type": "application/json" },
    data: {
      license_plate: "51A-999.88",
      vehicle_type: "car",
      brand: "Toyota",
      model: "Camry",
      color: "White",
      is_default: true,
    },
  });
  if (vehicleRes.status() === 201) {
    console.log("✅ Test vehicle created");
  } else {
    console.log(`ℹ️ Vehicle creation: ${vehicleRes.status()}`);
  }
}

setup("authenticate as user", async ({ page }) => {
  // Ensure auth directory exists
  fs.mkdirSync(AUTH_DIR, { recursive: true });

  // Ensure test user exists
  await ensureTestUser(page.request);

  // Login via UI
  await page.goto("/login");
  await page.waitForLoadState("networkidle");

  // Fill login form
  await page.locator("#email").fill(USER_CREDENTIALS.email);
  await page.locator("#password").fill(USER_CREDENTIALS.password);
  await page.getByRole("button", { name: /login|sign in|đăng nhập/i }).click();

  // Wait for redirect to dashboard or home
  await page.waitForURL("/", { timeout: 15000 }).catch(() => {
    // May redirect elsewhere
  });

  // Wait a bit for cookies to be set
  await page.waitForTimeout(2000);

  // Save auth state
  await page.context().storageState({ path: path.join(AUTH_DIR, "user.json") });
  console.log("✅ User auth state saved");

  // Seed test data
  const cookies = await page.context().cookies();
  await ensureTestDataForUser(page.request, cookies);
});

setup("authenticate as admin", async ({ page }) => {
  fs.mkdirSync(AUTH_DIR, { recursive: true });

  await page.goto("/login");
  await page.waitForLoadState("networkidle");

  await page.locator("#email").fill(ADMIN_CREDENTIALS.email);
  await page.locator("#password").fill(ADMIN_CREDENTIALS.password);
  await page.getByRole("button", { name: /login|sign in|đăng nhập/i }).click();

  await page.waitForURL("**/*", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(2000);

  await page
    .context()
    .storageState({ path: path.join(AUTH_DIR, "admin.json") });
  console.log("✅ Admin auth state saved");
});
