import { defineConfig, devices } from "@playwright/test";

/**
 * ParkSmart — Playwright E2E Test Configuration.
 *
 * Frontend runs on localhost:8080 (Vite dev server).
 * API goes through /api/* → gateway on localhost:8000.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  timeout: 60_000,

  use: {
    baseURL: "http://localhost:8080",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    {
      name: "setup",
      testMatch: /global-setup\.ts/,
    },
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "./e2e/.auth/user.json",
      },
      dependencies: ["setup"],
    },
    {
      name: "admin",
      testMatch: /admin\..*\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        storageState: "./e2e/.auth/admin.json",
      },
      dependencies: ["setup"],
    },
  ],

  /* Start Vite dev server before tests */
  webServer: {
    command: "npm run dev",
    url: "http://localhost:8080",
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
