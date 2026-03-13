/**
 * Services Index
 * Centralized export for all services
 *
 * Architecture:
 * ├── api/           - Pure HTTP calls (Axios) - snake_case params (Django REST)
 * │   ├── axios.client.ts
 * │   ├── endpoints.ts
 * │   ├── auth.api.ts
 * │   ├── booking.api.ts
 * │   ├── parking.api.ts
 * │   ├── vehicle.api.ts
 * │   ├── notification.api.ts
 * │   ├── incident.api.ts
 * │   └── admin.api.ts
 * │
 * ├── business/      - Business logic + Redux + WebSocket - camelCase params
 * │   ├── auth.service.ts
 * │   ├── booking.service.ts
 * │   ├── parking.service.ts
 * │   ├── vehicle.service.ts
 * │   ├── notification.service.ts
 * │   ├── incident.service.ts
 * │   └── admin.service.ts
 * │
 * └── websocket.service.ts - WebSocket connection management
 *
 * Usage Pattern:
 * - Components use business services (camelCase): authService.login()
 * - Business services call API layer (snake_case): authApi.login()
 * - API layer communicates with Django REST backend
 */

// =====================
// API Layer (HTTP calls only - snake_case)
// =====================
export { default as apiClient } from "./api/axios.client";
export { buildPaginationParams, extractErrorMessage } from "./api/axios.client";
export { ENDPOINTS } from "./api/endpoints";

// Individual API modules
export { authApi, handleAuthError } from "./api/auth.api";
export { bookingApi } from "./api/booking.api";
export { parkingApi } from "./api/parking.api";
export { vehicleApi } from "./api/vehicle.api";
export { notificationApi } from "./api/notification.api";
export { incidentApi } from "./api/incident.api";
export { adminApi } from "./api/admin.api";
export { chatbotApi } from "./api/chatbot.api";
export { aiApi } from "./api/ai.api";
export type {
  BanknoteRecognitionResponse,
  BanknoteQualityInfo,
  BanknoteDetectionInfo,
  DetectionMode,
} from "./api/ai.api";
export type {
  ChatMessage as ChatbotMessage,
  ChatResponse as ChatbotResponse,
  QuickAction as ChatbotQuickAction,
  Conversation as ChatbotConversation,
  ActiveConversationResponse,
  FeedbackRequest,
} from "./api/chatbot.api";

// =====================
// Business Logic Layer (Redux + WebSocket - camelCase)
// =====================
export {
  authService,
  parkingService,
  bookingService,
  vehicleService,
  notificationService,
  incidentService,
  adminService,
} from "./business";

// =====================
// WebSocket Service
// =====================
export {
  websocketService,
  WSMessageType,
  useWebSocket,
} from "./websocket.service";

// =====================
// API Types (snake_case - match Django REST)
// =====================
export type {
  DjangoPaginatedResponse,
  PaginationParams,
  ApiResponse,
  ApiErrorResponse,
} from "./api/axios.client";

export type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  OAuthUrlResponse,
} from "./api/auth.api";

export type {
  GetBookingsParams,
  CreateBookingRequest,
  CreateBookingResponse,
  CheckInRequest,
  CheckOutRequest,
  PaymentRequest,
  PaymentResponse,
  RevenueSummary,
  DailyRevenueItem,
  HourlyRevenueItem,
} from "./api/booking.api";

export type {
  GetLotsParams,
  GetZonesParams,
  GetSlotsParams,
  CheckAvailabilityParams,
  CheckAvailabilityResponse,
} from "./api/parking.api";

export type {
  Vehicle,
  CreateVehicleRequest,
  UpdateVehicleRequest,
} from "./api/vehicle.api";

export type { GetNotificationsParams } from "./api/notification.api";

export type {
  Incident,
  IncidentType,
  IncidentStatus,
  ReportIncidentRequest,
  ReportIncidentResponse,
} from "./api/incident.api";

export type {
  User as AdminUser,
  GetUsersParams,
  DashboardStats,
  RevenueReport,
  IncidentReport,
  SystemConfig,
  CreateUserData,
} from "./api/admin.api";

export type { WebSocketMessage } from "./websocket.service";

// =====================
// Business Types (camelCase - used by components)
// =====================
export type {
  LoginCredentials,
  RegisterData,
  AuthResult,
  SearchParkingParams,
  SlotAvailabilityCheck,
  BookingFilters,
  BookingResult,
  CheckInOutResult,
  VehicleResult,
  NotificationFilters,
  NotificationPreferences,
  ReportIncidentData,
  IncidentResult,
  UserFilters,
  RevenueReportParams,
  OperationResult,
} from "./business";

// =====================
// Domain Types
// =====================
export type {
  VehicleType,
  PackageType,
  PaymentType,
  CheckInStatus,
  PaymentStatus,
  ParkingLot,
  Floor,
  Zone,
  CarSlot,
  Camera,
  Booking,
  DashboardStats as DashboardStatsType,
  MapNode,
  MapEdge,
  DirectionStep,
  BankInfo,
} from "@/types/parking";
