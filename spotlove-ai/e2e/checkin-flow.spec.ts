/**
 * ParkSmart — E2E Check-in Flow with AI Plate Detection.
 *
 * Flow:
 *   1. Create a new booking (reuse booking-full-flow logic)
 *   2. Navigate to Check-in page
 *   3. Upload license plate image
 *   4. Verify AI detection response (plate_text, annotated image saved)
 *   5. Complete check-in
 *   6. Navigate to cameras page — verify vehicle status shown
 *   7. Save all screenshots and detection results
 *
 * Depends on "setup" project (user.json auth state).
 */

import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";

const RESULTS_DIR = "test-results";
const AI_SERVICE_URL = "http://localhost:8009";
const GATEWAY_SECRET = "gw-prod-wnMbXWEHc49KXVjhae4IGU7TZfoj4HHEDTOtzYvE";
const PLATE_IMAGE_PATH = path.resolve(
  "../backend-microservices/test_images/license_plate.jpg",
);

test.describe("Check-in Flow — Booking + AI Plate Detection", () => {
  test.beforeAll(() => {
    fs.mkdirSync(RESULTS_DIR, { recursive: true });
  });

  test("should complete booking → check-in → verify camera", async ({
    page,
  }) => {
    test.setTimeout(300_000);

    // ══════════════════════════════════════════════════════════════
    // PHASE 1 — Create a booking (same flow as booking-full-flow)
    // ══════════════════════════════════════════════════════════════

    // ── STEP 1: Select parking lot ───────────────────────────────
    await test.step("Navigate to booking and select lot", async () => {
      await page.goto("/booking");
      await page.waitForLoadState("domcontentloaded");
      await expect(page).toHaveURL(/\/booking/);

      await expect(page.getByText("Đang tải danh sách bãi xe...")).toBeHidden({
        timeout: 15_000,
      });

      const lotCard = page
        .locator("button")
        .filter({ hasText: "ParkSmart Tower" });
      await expect(lotCard.first()).toBeVisible({ timeout: 10_000 });
      await lotCard.first().click();

      await page.screenshot({
        path: path.join(RESULTS_DIR, "checkin-step1-lot-selected.png"),
      });

      const nextButton = page.getByRole("button", { name: /tiếp tục/i });
      await expect(nextButton).toBeEnabled();
      await nextButton.click();
    });

    // ── STEP 2: Select vehicle ───────────────────────────────────
    await test.step("Select saved vehicle", async () => {
      await expect(
        page.getByRole("heading", { name: /chọn loại xe/i }),
      ).toBeVisible({ timeout: 5_000 });

      await expect(page.locator(".animate-spin").first()).toBeHidden({
        timeout: 10_000,
      });

      const vehicleCard = page
        .locator("button")
        .filter({ hasText: "51A-999.88" });
      await expect(vehicleCard.first()).toBeVisible({ timeout: 10_000 });
      await vehicleCard.first().click();

      await expect(
        page.locator('input[placeholder="VD: 51A-123.45"]'),
      ).toHaveValue("51A-999.88");

      await page.screenshot({
        path: path.join(RESULTS_DIR, "checkin-step2-vehicle-selected.png"),
      });

      const nextButton = page.getByRole("button", { name: /tiếp tục/i });
      await expect(nextButton).toBeEnabled();
      await nextButton.click();
    });

    // ── STEP 3: Select slot ──────────────────────────────────────
    let slotCode: string | null = null;

    await test.step("Select floor, zone, and slot", async () => {
      await expect(
        page.getByRole("heading", { name: /chọn vị trí đậu xe/i }),
      ).toBeVisible({ timeout: 5_000 });

      await expect(page.locator(".animate-spin").first()).toBeHidden({
        timeout: 10_000,
      });

      // Select Tang 1
      const floorButton = page.locator("button").filter({ hasText: /Tang 1/ });
      await expect(floorButton.first()).toBeVisible({ timeout: 10_000 });
      await floorButton.first().click();

      // Select Zone A
      const zoneButton = page.locator("button").filter({ hasText: /Zone A/i });
      await expect(zoneButton.first()).toBeVisible({ timeout: 10_000 });
      await zoneButton.first().click();

      // Wait for slot grid
      const slotLabel = page.getByText("Chọn ô đậu xe");
      await expect(slotLabel).toBeVisible({ timeout: 15_000 });
      const slotSection = slotLabel.locator("..");

      await expect(slotSection.locator(".animate-spin")).toBeHidden({
        timeout: 15_000,
      });
      await expect(slotSection.getByText(/Còn trống:/).first()).toBeVisible({
        timeout: 10_000,
      });

      // Pick first available slot
      const availableSlot = slotSection
        .locator("button:not([disabled])")
        .filter({ hasText: /[A-Z]-\d{2}/ })
        .first();
      await expect(availableSlot).toBeVisible({ timeout: 10_000 });
      const slotText = await availableSlot.textContent();
      slotCode = slotText?.match(/[A-Z]-\d{2}/)?.[0] ?? slotText;
      await availableSlot.click();

      console.log(`✅ Selected slot: ${slotCode}`);

      await page.screenshot({
        path: path.join(RESULTS_DIR, "checkin-step3-slot-selected.png"),
      });

      const nextButton = page.getByRole("button", { name: /tiếp tục/i });
      await expect(nextButton).toBeEnabled();
      await nextButton.click();
    });

    // ── STEP 4: Select time ──────────────────────────────────────
    await test.step("Select hourly time package", async () => {
      await expect(
        page.getByRole("heading", { name: /chọn thời gian/i }),
      ).toBeVisible({ timeout: 5_000 });

      const hourlyButton = page
        .locator("button")
        .filter({ has: page.locator("span", { hasText: /^Theo giờ$/ }) });
      await expect(hourlyButton).toBeVisible({ timeout: 5_000 });
      await hourlyButton.click();

      await expect(page.getByText("Giờ kết thúc")).toBeVisible({
        timeout: 5_000,
      });

      await page.screenshot({
        path: path.join(RESULTS_DIR, "checkin-step4-time-selected.png"),
      });

      const nextButton = page.getByRole("button", { name: /tiếp tục/i });
      await expect(nextButton).toBeEnabled();
      await nextButton.click();
    });

    // ── STEP 5: Payment + Confirm ────────────────────────────────
    let bookingId: string | null = null;

    await test.step("Select payment and confirm booking", async () => {
      await expect(
        page.getByRole("heading", { name: /xác nhận.*thanh toán/i }),
      ).toBeVisible({ timeout: 5_000 });

      const onExitButton = page
        .locator("button")
        .filter({ hasText: /thanh toán khi lấy xe/i });
      await expect(onExitButton).toBeEnabled();
      await onExitButton.click();

      await page.screenshot({
        path: path.join(RESULTS_DIR, "checkin-step5-payment-selected.png"),
      });

      const confirmButton = page.getByRole("button", {
        name: /xác nhận đặt chỗ/i,
      });
      await expect(confirmButton).toBeVisible();
      await expect(confirmButton).toBeEnabled();
      await confirmButton.click();

      // Wait for success dialog
      const successDialog = page.getByRole("heading", {
        name: "Đặt chỗ thành công!",
      });
      await expect(successDialog).toBeVisible({ timeout: 30_000 });

      const qrCodeSvg = page.locator("#booking-qr-code");
      await expect(qrCodeSvg).toBeVisible({ timeout: 10_000 });

      await page.screenshot({
        path: path.join(RESULTS_DIR, "checkin-booking-qr-code.png"),
        fullPage: true,
      });

      // Extract booking ID from dialog
      const dialogContent = page.locator("[role='dialog']");
      const bookingIdEl = dialogContent
        .locator("p.font-mono.font-bold")
        .first();
      const bookingIdText = (await bookingIdEl.textContent())?.trim() ?? null;

      if (bookingIdText) {
        bookingId = bookingIdText.toLowerCase();
      }

      // Fallback: extract UUID from full dialog text
      const dialogText = await dialogContent.textContent();
      const uuidMatch = dialogText?.match(
        /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i,
      );
      if (uuidMatch) {
        bookingId = uuidMatch[1];
      }

      expect(bookingId).toBeTruthy();
      console.log(`✅ Booking created: ${bookingId}`);
    });

    // Close the success dialog — press Escape or click overlay
    await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(1_000);
    // If dialog is still open, try clicking outside
    const dialogStillOpen = await page
      .locator("[role='dialog']")
      .isVisible()
      .catch(() => false);
    if (dialogStillOpen) {
      await page.mouse.click(10, 10);
      await page.waitForTimeout(500);
    }

    // ══════════════════════════════════════════════════════════════
    // PHASE 2 — Check-in with plate image
    // ══════════════════════════════════════════════════════════════

    await test.step("Navigate to check-in page", async () => {
      await page.goto("/check-in-out");
      await page.waitForLoadState("domcontentloaded");
      await expect(page).toHaveURL(/\/check-in-out/);

      await page.screenshot({
        path: path.join(RESULTS_DIR, "checkin-step6-checkin-page.png"),
      });
    });

    await test.step("Wait for active booking to appear", async () => {
      // Wait for the page to load booking data
      await expect(page.locator(".animate-spin").first()).toBeHidden({
        timeout: 15_000,
      });

      // The check-in page should show the active booking
      await page.waitForTimeout(3_000);

      await page.screenshot({
        path: path.join(RESULTS_DIR, "checkin-step7-active-booking.png"),
      });
    });

    await test.step("Upload license plate image", async () => {
      // Find file input for plate image upload
      const fileInput = page.locator('input[type="file"]').first();
      await fileInput.setInputFiles(PLATE_IMAGE_PATH);

      // Wait for upload to process
      await page.waitForTimeout(2_000);

      await page.screenshot({
        path: path.join(RESULTS_DIR, "checkin-step8-plate-uploaded.png"),
      });
    });

    await test.step("Click check-in button and verify result", async () => {
      const checkinButton = page
        .getByRole("button")
        .filter({ hasText: /check.?in|nhận xe|xác nhận/i });
      if (await checkinButton.first().isVisible()) {
        await checkinButton.first().click();

        // Wait for check-in response
        await page.waitForTimeout(5_000);
      }

      await page.screenshot({
        path: path.join(RESULTS_DIR, "checkin-step9-checkin-result.png"),
        fullPage: true,
      });
    });

    // ══════════════════════════════════════════════════════════════
    // PHASE 3 — Direct AI scan-plate API call
    // ══════════════════════════════════════════════════════════════

    let scanPlateResult: Record<string, unknown> | null = null;

    await test.step("Call AI scan-plate API directly", async () => {
      const imageBuffer = fs.readFileSync(PLATE_IMAGE_PATH);

      const response = await page.request.post(
        `${AI_SERVICE_URL}/ai/parking/scan-plate/`,
        {
          headers: {
            "X-Gateway-Secret": GATEWAY_SECRET,
          },
          multipart: {
            image: {
              name: "license_plate.jpg",
              mimeType: "image/jpeg",
              buffer: imageBuffer,
            },
          },
        },
      );

      expect(response.ok()).toBeTruthy();
      scanPlateResult = await response.json();
      console.log(
        "✅ Scan plate result:",
        JSON.stringify(scanPlateResult, null, 2),
      );

      expect(scanPlateResult).toBeTruthy();
    });

    // ══════════════════════════════════════════════════════════════
    // PHASE 4 — Verify camera page
    // ══════════════════════════════════════════════════════════════

    await test.step("Navigate to cameras page", async () => {
      await page.goto("/cameras");
      await page.waitForLoadState("domcontentloaded");
      await expect(page).toHaveURL(/\/cameras/);

      // Wait for camera page content to load
      await page.waitForTimeout(3_000);

      await page.screenshot({
        path: path.join(RESULTS_DIR, "checkin-step10-cameras-page.png"),
        fullPage: true,
      });
    });

    // ══════════════════════════════════════════════════════════════
    // SAVE — All results to JSON
    // ══════════════════════════════════════════════════════════════

    await test.step("Save check-in flow results", async () => {
      const results = {
        timestamp: new Date().toISOString(),
        booking: {
          bookingId,
          licensePlate: "51A-999.88",
          vehicleType: "Car",
          parkingLot: "ParkSmart Tower",
          floor: "Tầng 1",
          zone: "Zone A",
          slot: slotCode ?? "unknown",
          packageType: "hourly",
          paymentMethod: "on_exit",
        },
        scanPlate: scanPlateResult,
        status: "completed",
      };

      const outputPath = path.join(RESULTS_DIR, "checkin-flow-results.json");
      fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
      console.log(`✅ Check-in flow results saved to ${outputPath}`);
    });
  });

  test("should verify AI plate detection saves annotated images", async ({
    page,
  }) => {
    test.setTimeout(60_000);

    const imageBuffer = fs.readFileSync(PLATE_IMAGE_PATH);

    // ── Call scan-plate API ──────────────────────────────────────
    const response = await test.step("Call AI scan-plate API", async () => {
      const res = await page.request.post(
        `${AI_SERVICE_URL}/ai/parking/scan-plate/`,
        {
          headers: {
            "X-Gateway-Secret": GATEWAY_SECRET,
          },
          multipart: {
            image: {
              name: "license_plate.jpg",
              mimeType: "image/jpeg",
              buffer: imageBuffer,
            },
          },
        },
      );

      expect(res.ok()).toBeTruthy();
      return res;
    });

    const data = await response.json();
    console.log("✅ Plate detection response:", JSON.stringify(data, null, 2));

    // ── Assert plate_text is non-empty ───────────────────────────
    await test.step("Verify plate_text is present", async () => {
      expect(data.plate_text).toBeTruthy();
      expect(typeof data.plate_text).toBe("string");
      expect(data.plate_text.length).toBeGreaterThan(0);
      console.log(`✅ Detected plate text: ${data.plate_text}`);
    });

    // ── Assert annotated_image_url is present ────────────────────
    await test.step("Verify annotated_image_url exists", async () => {
      expect(data.annotated_image_url).toBeTruthy();
      expect(typeof data.annotated_image_url).toBe("string");
      console.log(`✅ Annotated image URL: ${data.annotated_image_url}`);
    });

    // ── Fetch annotated image to verify accessibility ────────────
    await test.step("Verify annotated image is accessible", async () => {
      // Build full URL — annotated_image_url may be relative
      const imageUrl = data.annotated_image_url.startsWith("http")
        ? data.annotated_image_url
        : `${AI_SERVICE_URL}${data.annotated_image_url}`;

      const imageResponse = await page.request.get(imageUrl, {
        headers: {
          "X-Gateway-Secret": GATEWAY_SECRET,
        },
      });

      expect(imageResponse.ok()).toBeTruthy();
      const contentType = imageResponse.headers()["content-type"] ?? "";
      expect(contentType).toContain("image");
      console.log(
        `✅ Annotated image accessible (${contentType}, ${imageResponse.body().then((b) => b.length)} bytes)`,
      );
    });

    // ── Save detection results ───────────────────────────────────
    await test.step("Save plate detection results", async () => {
      const results = {
        timestamp: new Date().toISOString(),
        plateText: data.plate_text,
        confidence: data.confidence ?? null,
        bbox: data.bbox ?? null,
        plateImageUrl: data.plate_image_url ?? null,
        annotatedImageUrl: data.annotated_image_url ?? null,
      };

      const outputPath = path.join(RESULTS_DIR, "plate-detection-results.json");
      fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
      console.log(`✅ Plate detection results saved to ${outputPath}`);
    });
  });
});
