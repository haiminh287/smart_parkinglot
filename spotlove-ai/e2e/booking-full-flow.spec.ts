/**
 * ParkSmart — E2E Full Booking Flow.
 *
 * Creates an hourly booking at ParkSmart Tower → Tầng 1 → Zone A (Car),
 * selects on_exit payment, and captures the QR code for Unity simulation.
 *
 * Note: Tầng 2 only has Motorbike zones (C, D). Car zones are on Tầng 1 and 3.
 * Depends on "setup" project (user.json auth state).
 */

import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";

const RESULTS_DIR = "test-results";

test.describe("Full Booking Flow — ParkSmart Tower", () => {
  test.beforeAll(() => {
    fs.mkdirSync(RESULTS_DIR, { recursive: true });
  });

  test("should create hourly booking and get QR code", async ({ page }) => {
    test.setTimeout(120_000);
    // ── Navigate to booking page ──────────────────────────────────
    await page.goto("/booking");
    await page.waitForLoadState("domcontentloaded");
    await expect(page).toHaveURL(/\/booking/);

    // Ensure the "Đặt chỗ" (standard) tab is active by default
    await expect(
      page.getByRole("tab", { name: /đặt chỗ|chuẩn/i }),
    ).toHaveAttribute("data-state", "active");

    // ══════════════════════════════════════════════════════════════
    // STEP 1 — Chọn bãi: Select "ParkSmart Tower"
    // ══════════════════════════════════════════════════════════════
    // Wait for parking lots to finish loading
    await expect(page.getByText("Đang tải danh sách bãi xe...")).toBeHidden({
      timeout: 15_000,
    });

    // Click the lot card that contains "ParkSmart Tower"
    const lotCard = page
      .locator("button")
      .filter({ hasText: "ParkSmart Tower" });
    await expect(lotCard.first()).toBeVisible({ timeout: 10_000 });
    await lotCard.first().click();

    await page.screenshot({
      path: path.join(RESULTS_DIR, "step1-lot-selected.png"),
    });

    // Advance to step 2
    const nextButton = page.getByRole("button", { name: /tiếp tục/i });
    await expect(nextButton).toBeEnabled();
    await nextButton.click();

    // ══════════════════════════════════════════════════════════════
    // STEP 2 — Chọn xe: Select saved vehicle 51A-999.88 (Car)
    // ══════════════════════════════════════════════════════════════
    await expect(
      page.getByRole("heading", { name: /chọn loại xe/i }),
    ).toBeVisible({ timeout: 5_000 });

    // Wait for saved vehicles to load (spinner disappears)
    await expect(page.locator(".animate-spin").first()).toBeHidden({
      timeout: 10_000,
    });

    // Click the saved vehicle card containing "51A-999.88"
    const vehicleCard = page
      .locator("button")
      .filter({ hasText: "51A-999.88" });
    await expect(vehicleCard.first()).toBeVisible({ timeout: 10_000 });
    await vehicleCard.first().click();

    // Confirm the license plate input was auto-filled
    await expect(
      page.locator('input[placeholder="VD: 51A-123.45"]'),
    ).toHaveValue("51A-999.88");

    await page.screenshot({
      path: path.join(RESULTS_DIR, "step2-vehicle-selected.png"),
    });

    // Advance to step 3
    await expect(nextButton).toBeEnabled();
    await nextButton.click();

    // ══════════════════════════════════════════════════════════════
    // STEP 3 — Chọn vị trí: Tầng 1 → Zone A → first available slot
    //   (Tầng 2 only has Motorbike zones, Tầng 1 has Car zones)
    // ══════════════════════════════════════════════════════════════
    await expect(
      page.getByRole("heading", { name: /chọn vị trí đậu xe/i }),
    ).toBeVisible({ timeout: 5_000 });

    // Wait for floors to load
    await expect(page.locator(".animate-spin").first()).toBeHidden({
      timeout: 10_000,
    });

    // Select "Tầng 1" (has Car zones A and B)
    const floorButton = page.locator("button").filter({ hasText: /Tầng 1/ });
    await expect(floorButton.first()).toBeVisible({ timeout: 10_000 });
    await floorButton.first().click();

    // Wait for zones to appear and select "Zone A" (Car, 21 available)
    const zoneButton = page.locator("button").filter({ hasText: /Zone A/i });
    await expect(zoneButton.first()).toBeVisible({ timeout: 10_000 });
    await zoneButton.first().click();

    // Wait for SlotGrid label to appear (only renders after zone selected + Car type)
    const slotLabel = page.getByText("Chọn ô đậu xe");
    await expect(slotLabel).toBeVisible({ timeout: 15_000 });

    // The slot section is the parent div containing both the label and SlotGrid
    const slotSection = slotLabel.locator("..");

    // Wait for loading spinner inside SlotGrid to disappear
    await expect(slotSection.locator(".animate-spin")).toBeHidden({
      timeout: 15_000,
    });

    // Wait for "Còn trống:" stats to confirm slots are loaded
    await expect(slotSection.getByText(/Còn trống:/).first()).toBeVisible({
      timeout: 10_000,
    });

    // Click the first available slot — slot codes match pattern "A-01", "A-02", etc.
    const availableSlot = slotSection
      .locator("button:not([disabled])")
      .filter({ hasText: /[A-Z]-\d{2}/ })
      .first();
    await expect(availableSlot).toBeVisible({ timeout: 10_000 });
    const slotText = await availableSlot.textContent();
    const slotCode = slotText?.match(/[A-Z]-\d{2}/)?.[0] ?? slotText;
    await availableSlot.click();

    console.log(`✅ Selected slot: ${slotCode}`);

    await page.screenshot({
      path: path.join(RESULTS_DIR, "step3-slot-selected.png"),
    });

    // Advance to step 4
    await expect(nextButton).toBeEnabled();
    await nextButton.click();

    // ══════════════════════════════════════════════════════════════
    // STEP 4 — Chọn thời gian: Hourly package, today, 08:00–17:00
    // ══════════════════════════════════════════════════════════════
    await expect(
      page.getByRole("heading", { name: /chọn thời gian/i }),
    ).toBeVisible({ timeout: 5_000 });

    // Select "Theo giờ" (button text includes subtitle "Linh hoạt, tính phí theo giờ")
    const hourlyButton = page
      .locator("button")
      .filter({ has: page.locator("span", { hasText: /^Theo giờ$/ }) });
    await expect(hourlyButton).toBeVisible({ timeout: 5_000 });
    await hourlyButton.click();

    // After switching to hourly, start=08:00 and end=17:00 are defaults.
    // Wait for the hourly time inputs to appear.
    await expect(page.getByText("Giờ kết thúc")).toBeVisible({
      timeout: 5_000,
    });

    await page.screenshot({
      path: path.join(RESULTS_DIR, "step4-time-selected.png"),
    });

    // Advance to step 5
    await expect(nextButton).toBeEnabled();
    await nextButton.click();

    // ══════════════════════════════════════════════════════════════
    // STEP 5 — Thanh toán: on_exit payment → Confirm
    // ══════════════════════════════════════════════════════════════
    await expect(
      page.getByRole("heading", { name: /xác nhận.*thanh toán/i }),
    ).toBeVisible({ timeout: 5_000 });

    // Select "Thanh toán khi lấy xe"
    const onExitButton = page
      .locator("button")
      .filter({ hasText: /thanh toán khi lấy xe/i });
    await expect(onExitButton).toBeEnabled();
    await onExitButton.click();

    await page.screenshot({
      path: path.join(RESULTS_DIR, "step5-payment-selected.png"),
    });

    // Click "Xác nhận đặt chỗ" (the main action button at step 5)
    const confirmButton = page.getByRole("button", {
      name: /xác nhận đặt chỗ/i,
    });
    await expect(confirmButton).toBeVisible();
    await expect(confirmButton).toBeEnabled();
    await confirmButton.click();

    // ══════════════════════════════════════════════════════════════
    // VERIFY — QR code dialog appears
    // ══════════════════════════════════════════════════════════════
    const successDialog = page.getByRole("heading", {
      name: "Đặt chỗ thành công!",
    });
    await expect(successDialog).toBeVisible({ timeout: 30_000 });

    // Wait for QR code SVG to render
    const qrCodeSvg = page.locator("#booking-qr-code");
    await expect(qrCodeSvg).toBeVisible({ timeout: 10_000 });

    // Take the most important screenshot — the QR code
    await page.screenshot({
      path: path.join(RESULTS_DIR, "booking-qr-code.png"),
      fullPage: true,
    });

    // ══════════════════════════════════════════════════════════════
    // EXTRACT — Save booking data to JSON for Unity consumption
    // ══════════════════════════════════════════════════════════════

    // Extract the QR code data from the SVG element
    // The BookingQRCode component embeds JSON in the QR with: id, plate, zone, slot, dates, type
    // We can also grab visible text from the dialog for additional context

    const dialogContent = page.locator("[role='dialog']");

    // Extract booking ID — rendered as font-mono bold text under "Mã đặt chỗ"
    const bookingIdEl = dialogContent.locator("p.font-mono.font-bold").first();
    const bookingIdText = (await bookingIdEl.textContent())?.trim() ?? null;

    // Extract the QR value by reading the qrData from the component
    // qrcode.react doesn't store value in DOM attrs, so parse from dialog text
    const dialogText = await dialogContent.textContent();

    // Build output for Unity
    const bookingOutput: Record<string, unknown> = {
      timestamp: new Date().toISOString(),
      licensePlate: "51A-999.88",
      vehicleType: "Car",
      parkingLot: "ParkSmart Tower",
      floor: "Tầng 1",
      zone: "Zone A",
      slot: slotCode || "unknown",
      packageType: "hourly",
      startTime: `${new Date().toISOString().split("T")[0]}T08:00:00`,
      endTime: `${new Date().toISOString().split("T")[0]}T17:00:00`,
      paymentMethod: "on_exit",
    };

    // Set booking ID from the displayed text
    if (bookingIdText) {
      bookingOutput.bookingId = bookingIdText.toLowerCase();
    }

    // Also try to extract the booking ID from the dialog text as fallback
    const bookingIdMatch = dialogText?.match(
      /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i,
    );
    if (bookingIdMatch) {
      bookingOutput.bookingId = bookingIdMatch[1];
    }

    // Save to JSON for Unity simulation
    const outputPath = path.join(RESULTS_DIR, "booking-for-unity.json");
    fs.writeFileSync(outputPath, JSON.stringify(bookingOutput, null, 2));
    console.log(`✅ Booking data saved to ${outputPath}`);
    console.log(JSON.stringify(bookingOutput, null, 2));

    // Final assertion: QR code and success message are visible
    await expect(successDialog).toBeVisible();
    await expect(qrCodeSvg).toBeVisible();
  });
});
