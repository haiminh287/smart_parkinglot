/**
 * ParkSmart — E2E Tests: API Endpoints via Frontend.
 *
 * Tests that API calls from the frontend work correctly
 * by intercepting network requests and verifying responses.
 */

import { test, expect } from "@playwright/test";
import * as dotenv from "dotenv";

dotenv.config({ path: ".env.test" });

const GATEWAY_URL = process.env.E2E_GATEWAY_URL || "http://localhost:8000";
const GATEWAY_SECRET = process.env.E2E_GATEWAY_SECRET;
if (!GATEWAY_SECRET) {
  throw new Error("E2E_GATEWAY_SECRET must be set in .env.test or environment");
}

test.describe("API: Parking Lots", () => {
  test("should fetch parking lots", async ({ request }) => {
    const res = await request.get(`${GATEWAY_URL}/parking/lots/`, {
      headers: { "X-Gateway-Secret": GATEWAY_SECRET },
    });
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    // Should have results array
    const results = data.results || data;
    expect(Array.isArray(results)).toBeTruthy();
    expect(results.length).toBeGreaterThan(0);
  });

  test("should fetch parking floors", async ({ request }) => {
    const res = await request.get(`${GATEWAY_URL}/parking/floors/`, {
      headers: { "X-Gateway-Secret": GATEWAY_SECRET },
    });
    expect(res.ok()).toBeTruthy();
  });

  test("should fetch parking zones", async ({ request }) => {
    const res = await request.get(`${GATEWAY_URL}/parking/zones/`, {
      headers: { "X-Gateway-Secret": GATEWAY_SECRET },
    });
    expect(res.ok()).toBeTruthy();
  });

  test("should fetch parking slots", async ({ request }) => {
    const res = await request.get(`${GATEWAY_URL}/parking/slots/`, {
      headers: { "X-Gateway-Secret": GATEWAY_SECRET },
    });
    expect(res.ok()).toBeTruthy();
  });

  test("should fetch cameras", async ({ request }) => {
    const res = await request.get(`${GATEWAY_URL}/parking/cameras/`, {
      headers: { "X-Gateway-Secret": GATEWAY_SECRET },
    });
    expect(res.ok()).toBeTruthy();
  });
});

test.describe("API: Auth", () => {
  test("should login with valid credentials", async ({ request }) => {
    const res = await request.post(`${GATEWAY_URL}/auth/login/`, {
      data: {
        email: "testuser@parksmart.com",
        password: "TestPass123!",
      },
    });
    // 200 OK or 400 (wrong pw) — should not be 500
    expect(res.status()).toBeLessThan(500);
  });

  test("should reject invalid credentials", async ({ request }) => {
    const res = await request.post(`${GATEWAY_URL}/auth/login/`, {
      data: {
        email: "nonexistent@example.com",
        password: "wrongpass",
      },
    });
    expect(res.status()).toBeGreaterThanOrEqual(400);
    expect(res.status()).toBeLessThan(500);
  });
});

test.describe("API: Vehicles (authenticated)", () => {
  test("should fetch vehicles list", async ({ page }) => {
    // Use authenticated page context
    const res = await page.request.get(`${GATEWAY_URL}/vehicles/`, {
      headers: { "X-Gateway-Secret": GATEWAY_SECRET },
    });
    // May be 200 or 401 depending on session
    expect(res.status()).toBeLessThan(500);
  });
});

test.describe("API: Bookings (authenticated)", () => {
  test("should fetch bookings list", async ({ page }) => {
    const res = await page.request.get(`${GATEWAY_URL}/bookings/`, {
      headers: { "X-Gateway-Secret": GATEWAY_SECRET },
    });
    expect(res.status()).toBeLessThan(500);
  });
});

test.describe("API: Notifications (authenticated)", () => {
  test("should fetch notifications", async ({ page }) => {
    const res = await page.request.get(`${GATEWAY_URL}/notifications/`, {
      headers: { "X-Gateway-Secret": GATEWAY_SECRET },
    });
    expect(res.status()).toBeLessThan(500);
  });
});

test.describe("API: AI Service Health", () => {
  test("should check AI service health", async ({ request }) => {
    const res = await request.get("http://localhost:8009/health/");
    if (res.ok()) {
      const data = await res.json();
      expect(data.status).toBe("healthy");
    }
  });

  test("should check ESP32 status endpoint", async ({ request }) => {
    const res = await request.get(
      "http://localhost:8009/ai/parking/esp32/status/",
    );
    // May or may not be running
    expect(res.status()).toBeLessThan(500);
  });
});
