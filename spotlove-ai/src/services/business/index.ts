/**
 * Business Services Index
 * Export all business logic services
 * 
 * Architecture:
 * - api/*.api.ts: Pure HTTP calls (Axios)
 * - business/*.service.ts: Business logic + Redux + WebSocket integration
 */

export { authService } from './auth.service';
export { parkingService } from './parking.service';
export { bookingService } from './booking.service';
export { vehicleService } from './vehicle.service';
export { notificationService } from './notification.service';
export { incidentService } from './incident.service';
export { adminService } from './admin.service';

// Re-export types for convenience
export type { LoginCredentials, RegisterData, AuthResult } from './auth.service';
export type { SearchParkingParams, SlotAvailabilityCheck } from './parking.service';
export type { BookingFilters, BookingResult, CheckInOutResult } from './booking.service';
export type { VehicleResult } from './vehicle.service';
export type { NotificationFilters, NotificationPreferences } from './notification.service';
export type { ReportIncidentData, IncidentResult } from './incident.service';
export type { UserFilters, RevenueReportParams, OperationResult } from './admin.service';
