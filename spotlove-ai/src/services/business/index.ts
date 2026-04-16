/**
 * Business Services Index
 * Export all business logic services
 *
 * Architecture:
 * - api/*.api.ts: Pure HTTP calls (Axios)
 * - business/*.service.ts: Business logic + Redux + WebSocket integration
 *
 * IMPORTANT: Pages/components/store should ONLY import from this layer,
 * never directly from api/*.api.ts files.
 */

export { authService } from "./auth.service";
export { parkingService } from "./parking.service";
export { bookingService } from "./booking.service";
export { vehicleService } from "./vehicle.service";
export { notificationService } from "./notification.service";
export { incidentService } from "./incident.service";
export { adminService } from "./admin.service";
export { aiService } from "./ai.service";
export { chatbotService } from "./chatbot.service";

// Re-export types for convenience
export type {
  LoginCredentials,
  RegisterData,
  AuthResult,
} from "./auth.service";
export type {
  SearchParkingParams,
  SlotAvailabilityCheck,
  Floor,
} from "./parking.service";
export type {
  BookingFilters,
  BookingResult,
  CheckInOutResult,
  PackagePricing,
  RevenueSummary,
  DailyRevenueItem,
  HourlyRevenueItem,
} from "./booking.service";
export type { VehicleResult, CreateVehicleData } from "./vehicle.service";
export type {
  NotificationFilters,
  NotificationPreferences,
} from "./notification.service";
export type {
  ReportIncidentData,
  IncidentResult,
  Incident,
  IncidentType,
} from "./incident.service";
export type {
  UserFilters,
  RevenueReportParams,
  OperationResult,
  User,
  DashboardStats,
  CreateUserData,
} from "./admin.service";

// AI Service types
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
  DetectionHistoryParams,
} from "./ai.service";
export { DENOMINATION_LABELS, DENOMINATION_COLORS } from "./ai.service";

// Chatbot Service types
export type {
  ChatMessage,
  ChatResponse,
  QuickAction,
  Conversation,
  ActiveConversationResponse,
  FeedbackRequest,
} from "./chatbot.service";
