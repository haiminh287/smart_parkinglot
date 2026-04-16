/**
 * AI Business Service
 * Business logic layer - handles AI operations (banknote, plate OCR, ESP32)
 *
 * Pattern: service.ts = Business Logic layer
 *          api.ts = Pure HTTP calls only
 */

import { aiApi } from "@/services/api/ai.api";
import type {
  BanknoteRecognitionResponse,
  BanknoteQualityInfo,
  BanknoteDetectionInfo,
  DetectionMode,
  PlateOCRResponse,
  CheckInResponse,
  CheckOutResponse,
  ESP32Response,
  ESP32CheckInRequest,
  ESP32CheckOutRequest,
  ESP32VerifySlotRequest,
  CashPaymentRequest,
  ESP32DeviceInfo,
  ESP32DeviceLog,
  ESP32DevicesResponse,
  ESP32DeviceLogsResponse,
  DetectionRecord,
  DetectionHistoryResponse,
  BarrierAction,
  GateEvent,
} from "@/services/api/ai.api";

// =====================
// Re-export Types for consumers
// =====================

export type {
  BanknoteRecognitionResponse,
  BanknoteQualityInfo,
  BanknoteDetectionInfo,
  DetectionMode,
  PlateOCRResponse,
  CheckInResponse,
  CheckOutResponse,
  ESP32Response,
  ESP32CheckInRequest,
  ESP32CheckOutRequest,
  ESP32VerifySlotRequest,
  CashPaymentRequest,
  ESP32DeviceInfo,
  ESP32DeviceLog,
  ESP32DevicesResponse,
  ESP32DeviceLogsResponse,
  DetectionRecord,
  DetectionHistoryResponse,
  BarrierAction,
  GateEvent,
};

// Re-export constants
export { DENOMINATION_LABELS, DENOMINATION_COLORS } from "@/services/api/ai.api";

// =====================
// Business Service Types
// =====================

export interface BanknoteDetectionResult {
  success: boolean;
  denomination: string | null;
  confidence: number;
  decision: string;
  message: string;
  processingTimeMs: number;
}

export interface PlateDetectionResult {
  success: boolean;
  plateText: string;
  confidence: number;
  message: string;
  processingTimeMs: number;
}

export interface DetectionHistoryParams {
  page?: number;
  pageSize?: number;
  plateText?: string;
  dateFrom?: string;
  dateTo?: string;
  action?: string;
}

// =====================
// AI Business Service
// =====================

export const aiService = {
  // ── Banknote Detection ──────────────────────────

  /**
   * Detect Vietnamese banknote denomination from an image
   */
  async detectBanknote(
    image: File,
    mode: DetectionMode = "full",
  ): Promise<BanknoteRecognitionResponse> {
    return aiApi.detectBanknote(image, mode);
  },

  // ── Plate OCR ───────────────────────────────────

  /**
   * Scan license plate from an image (OCR only, no booking check)
   */
  async scanPlate(image: File): Promise<PlateOCRResponse> {
    return aiApi.scanPlate(image);
  },

  /**
   * Web check-in with plate image and QR data
   */
  async checkIn(
    image: File,
    qrData: { bookingId: string; userId: string },
  ): Promise<CheckInResponse> {
    return aiApi.checkIn(image, qrData);
  },

  /**
   * Web check-out with plate image and QR data
   */
  async checkOut(
    image: File,
    qrData: { bookingId: string; userId: string },
  ): Promise<CheckOutResponse> {
    return aiApi.checkOut(image, qrData);
  },

  // ── ESP32 Gate Operations ───────────────────────

  /**
   * ESP32 gate-in check-in
   */
  async esp32CheckIn(data: ESP32CheckInRequest): Promise<ESP32Response> {
    return aiApi.esp32CheckIn(data);
  },

  /**
   * ESP32 gate-out check-out
   */
  async esp32CheckOut(data: ESP32CheckOutRequest): Promise<ESP32Response> {
    return aiApi.esp32CheckOut(data);
  },

  /**
   * ESP32 slot verification
   */
  async esp32VerifySlot(data: ESP32VerifySlotRequest): Promise<ESP32Response> {
    return aiApi.esp32VerifySlot(data);
  },

  /**
   * ESP32 cash payment at exit gate
   */
  async esp32CashPayment(data: CashPaymentRequest): Promise<ESP32Response> {
    return aiApi.esp32CashPayment(data);
  },

  // ── ESP32 Device Management ─────────────────────

  /**
   * Get list of all registered ESP32 devices
   */
  async getESP32Devices(): Promise<ESP32DevicesResponse> {
    return aiApi.getESP32Devices();
  },

  /**
   * Get logs for a specific ESP32 device
   */
  async getESP32DeviceLogs(deviceId: string): Promise<ESP32DeviceLogsResponse> {
    return aiApi.getESP32DeviceLogs(deviceId);
  },

  // ── Detection History ───────────────────────────

  /**
   * Get paginated detection history with optional filters
   */
  async getDetectionHistory(
    params?: DetectionHistoryParams,
  ): Promise<DetectionHistoryResponse> {
    return aiApi.getDetectionHistory({
      page: params?.page,
      page_size: params?.pageSize,
      plate_text: params?.plateText,
      date_from: params?.dateFrom,
      date_to: params?.dateTo,
      action: params?.action,
    });
  },
};
