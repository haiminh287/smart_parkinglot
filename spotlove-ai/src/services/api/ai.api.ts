/**
 * AI Service API — Banknote Recognition + Plate OCR + ESP32 Integration
 *
 * Endpoints:
 *   POST /ai/detect/banknote/          — Detect Vietnamese banknote denomination
 *   POST /ai/parking/scan-plate/       — Detect + OCR license plate
 *   POST /ai/parking/check-in/         — QR + plate check-in
 *   POST /ai/parking/check-out/        — QR + plate check-out
 *   POST /ai/parking/esp32/check-in/   — ESP32 gate-in
 *   POST /ai/parking/esp32/check-out/  — ESP32 gate-out
 *   POST /ai/parking/esp32/verify-slot/ — ESP32 slot verification
 *   POST /ai/parking/esp32/cash-payment/ — Cash payment at gate
 */

import apiClient from "./axios.client";

// ── Types ──────────────────────────────────────

export interface BanknoteQualityInfo {
  blurScore: number;
  exposureScore: number;
  status: string;
  message: string;
}

export interface BanknoteDetectionInfo {
  found: boolean;
  confidence: number;
  message: string;
}

export interface BanknoteRecognitionResponse {
  decision:
    | "accept"
    | "low_confidence"
    | "no_banknote"
    | "bad_quality"
    | "error";
  denomination: string | null;
  confidence: number;
  method: "color" | "ai_fallback" | "none";
  quality: BanknoteQualityInfo | null;
  detection: BanknoteDetectionInfo | null;
  allProbabilities: Record<string, number> | null;
  stagesExecuted: string[];
  processingTimeMs: number;
  processingTime: number;
  message: string;
  pipelineVersion: string;
}

export type DetectionMode = "full" | "fast";

// ── Plate OCR Types ────────────────────────────

export interface PlateOCRResponse {
  plateText: string;
  decision: string;
  confidence: number;
  detectionConfidence: number;
  isBlurry: boolean;
  blurScore: number;
  ocrMethod: string;
  rawCandidates: string[];
  warning: string | null;
  message: string;
  processingTimeMs: number;
}

export interface CheckInResponse {
  success: boolean;
  message: string;
  bookingId: string;
  plateText: string;
  bookingPlate: string;
  plateMatch: boolean;
  ocrConfidence: number;
  ocrWarning: string | null;
  booking: Record<string, unknown>;
  processingTimeMs: number;
}

export interface CheckOutResponse {
  success: boolean;
  message: string;
  bookingId: string;
  plateText: string;
  bookingPlate: string;
  plateMatch: boolean;
  ocrConfidence: number;
  ocrWarning: string | null;
  booking: Record<string, unknown>;
  processingTimeMs: number;
}

// ── ESP32 Types ────────────────────────────────

export type BarrierAction = "open" | "close" | "no_action";

export type GateEvent =
  | "check_in_success"
  | "check_in_failed"
  | "check_out_success"
  | "check_out_awaiting_payment"
  | "check_out_failed"
  | "verify_slot_success"
  | "verify_slot_failed";

export interface ESP32Response {
  success: boolean;
  event: GateEvent;
  barrierAction: BarrierAction;
  message: string;
  gateId: string;
  bookingId: string | null;
  plateText: string | null;
  amountDue: number | null;
  amountPaid: number | null;
  processingTimeMs: number;
  details: Record<string, unknown> | null;
}

export interface ESP32CheckInRequest {
  gateId: string;
  qrCameraUrl?: string;
  plateCameraUrl?: string;
  requestId?: string;
}

export interface ESP32CheckOutRequest {
  gateId: string;
  qrCameraUrl?: string;
  plateCameraUrl?: string;
  requestId?: string;
}

export interface ESP32VerifySlotRequest {
  slotCode: string;
  zoneId: string;
  gateId: string;
  qrCameraUrl?: string;
  requestId?: string;
}

export interface CashPaymentRequest {
  bookingId: string;
  imageBase64?: string;
  cameraUrl?: string;
  gateId: string;
  requestId?: string;
}

// ── Denomination Labels ────────────────────────

export const DENOMINATION_LABELS: Record<string, string> = {
  "1000": "1.000 VND",
  "2000": "2.000 VND",
  "5000": "5.000 VND",
  "10000": "10.000 VND",
  "20000": "20.000 VND",
  "50000": "50.000 VND",
  "100000": "100.000 VND",
  "200000": "200.000 VND",
  "500000": "500.000 VND",
};

export const DENOMINATION_COLORS: Record<string, string> = {
  "1000": "#8B7355",
  "2000": "#6B8E23",
  "5000": "#4682B4",
  "10000": "#DAA520",
  "20000": "#4169E1",
  "50000": "#DB7093",
  "100000": "#228B22",
  "200000": "#CD5C5C",
  "500000": "#00CED1",
};

// ── ESP32 Device Management Types ──────────────

export interface ESP32DeviceInfo {
  deviceId: string;
  ip: string;
  firmware: string;
  gpioConfig: {
    checkInPin?: number;
    checkOutPin?: number;
    [key: string]: number | undefined;
  };
  status: string;
  wifiRssi: number;
  lastSeen: string;
  registeredAt: string;
  isOnline: boolean;
  logCount: number;
}

export interface ESP32DeviceLog {
  timestamp: string;
  level: "info" | "warning" | "error";
  message: string;
}

export interface ESP32DevicesResponse {
  devices: ESP32DeviceInfo[];
}

export interface ESP32DeviceLogsResponse {
  deviceId: string;
  logs: ESP32DeviceLog[];
}

// ── Detection History Types ────────────────────

export interface DetectionRecord {
  id: string;
  plate_text: string;
  confidence: number;
  decision: string;
  image_url: string | null;
  bbox: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    confidence: number;
  } | null;
  camera_id: string | null;
  action: string;
  prediction_type: string;
  created_at: string;
  processing_time_ms: number | null;
}

export interface DetectionHistoryResponse {
  total: number;
  page: number;
  page_size: number;
  results: DetectionRecord[];
}

// ── API Methods ────────────────────────────────

export const aiApi = {
  /**
   * Detect Vietnamese banknote denomination from an image.
   */
  detectBanknote: async (
    image: File,
    mode: DetectionMode = "full",
  ): Promise<BanknoteRecognitionResponse> => {
    const formData = new FormData();
    formData.append("image", image);

    const response = await apiClient.post<BanknoteRecognitionResponse>(
      `/ai/detect/banknote/?mode=${mode}`,
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      },
    );
    return response.data;
  },

  /**
   * Scan license plate from an image — detect + OCR only, no booking check.
   */
  scanPlate: async (image: File): Promise<PlateOCRResponse> => {
    const formData = new FormData();
    formData.append("image", image);

    const response = await apiClient.post<PlateOCRResponse>(
      "/ai/parking/scan-plate/",
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return response.data;
  },

  /**
   * Check-in via web: upload plate image + QR data.
   */
  checkIn: async (
    image: File,
    qrData: { bookingId: string; userId: string },
  ): Promise<CheckInResponse> => {
    const formData = new FormData();
    formData.append("image", image);
    formData.append(
      "qr_data",
      JSON.stringify({
        booking_id: qrData.bookingId,
        user_id: qrData.userId,
      }),
    );

    const response = await apiClient.post<CheckInResponse>(
      "/ai/parking/check-in/",
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return response.data;
  },

  /**
   * Check-out via web: upload plate image + QR data.
   */
  checkOut: async (
    image: File,
    qrData: { bookingId: string; userId: string },
  ): Promise<CheckOutResponse> => {
    const formData = new FormData();
    formData.append("image", image);
    formData.append(
      "qr_data",
      JSON.stringify({
        booking_id: qrData.bookingId,
        user_id: qrData.userId,
      }),
    );

    const response = await apiClient.post<CheckOutResponse>(
      "/ai/parking/check-out/",
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return response.data;
  },

  // ── ESP32 Endpoints ──────────────────────────

  /**
   * ESP32 gate-in check-in (device calls this).
   */
  esp32CheckIn: async (data: ESP32CheckInRequest): Promise<ESP32Response> => {
    const response = await apiClient.post<ESP32Response>(
      "/ai/parking/esp32/check-in/",
      {
        gate_id: data.gateId,
        qr_camera_url: data.qrCameraUrl,
        plate_camera_url: data.plateCameraUrl,
        request_id: data.requestId,
      },
    );
    return response.data;
  },

  /**
   * ESP32 gate-out check-out (device calls this).
   */
  esp32CheckOut: async (data: ESP32CheckOutRequest): Promise<ESP32Response> => {
    const response = await apiClient.post<ESP32Response>(
      "/ai/parking/esp32/check-out/",
      {
        gate_id: data.gateId,
        qr_camera_url: data.qrCameraUrl,
        plate_camera_url: data.plateCameraUrl,
        request_id: data.requestId,
      },
    );
    return response.data;
  },

  /**
   * ESP32 slot verification (device calls this).
   */
  esp32VerifySlot: async (
    data: ESP32VerifySlotRequest,
  ): Promise<ESP32Response> => {
    const response = await apiClient.post<ESP32Response>(
      "/ai/parking/esp32/verify-slot/",
      {
        slot_code: data.slotCode,
        zone_id: data.zoneId,
        gate_id: data.gateId,
        qr_camera_url: data.qrCameraUrl,
        request_id: data.requestId,
      },
    );
    return response.data;
  },

  /**
   * ESP32 cash payment at exit gate (device calls this).
   */
  esp32CashPayment: async (
    data: CashPaymentRequest,
  ): Promise<ESP32Response> => {
    const response = await apiClient.post<ESP32Response>(
      "/ai/parking/esp32/cash-payment/",
      {
        booking_id: data.bookingId,
        image_base64: data.imageBase64,
        camera_url: data.cameraUrl,
        gate_id: data.gateId,
        request_id: data.requestId,
      },
    );
    return response.data;
  },

  // ── ESP32 Device Management ──────────────────

  /**
   * Get list of all registered ESP32 devices with status.
   */
  getESP32Devices: async (): Promise<ESP32DevicesResponse> => {
    const response = await apiClient.get<ESP32DevicesResponse>(
      "/ai/parking/esp32/devices",
    );
    return response.data;
  },

  /**
   * Get last 100 logs for a specific ESP32 device.
   */
  getESP32DeviceLogs: async (
    deviceId: string,
  ): Promise<ESP32DeviceLogsResponse> => {
    const response = await apiClient.get<ESP32DeviceLogsResponse>(
      `/ai/parking/esp32/devices/${deviceId}/logs`,
    );
    return response.data;
  },

  /**
   * Get paginated detection history with optional filters.
   */
  getDetectionHistory: async (params?: {
    page?: number;
    page_size?: number;
    plate_text?: string;
    date_from?: string;
    date_to?: string;
    action?: string;
  }): Promise<DetectionHistoryResponse> => {
    const response = await apiClient.get<DetectionHistoryResponse>(
      "/ai/parking/detections/",
      { params },
    );
    return response.data;
  },
};
