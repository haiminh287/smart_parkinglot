/**
 * Booking Business Service
 * Business logic layer - handles booking operations + payment flow
 *
 * Pattern: service.ts = Business Logic + Redux + WebSocket Integration
 *          api.ts = Pure HTTP calls only
 */

import { bookingApi } from "@/services/api/booking.api";
import type {
  PackagePricingResponse,
  RevenueSummary as ApiRevenueSummary,
  DailyRevenueItem as ApiDailyRevenueItem,
  HourlyRevenueItem as ApiHourlyRevenueItem,
  ExtendBookingResponse,
} from "@/services/api/booking.api";
import { websocketService } from "@/services/websocket.service";
import { store } from "@/store";
import {
  setSelectedBooking,
  updateBookingStatus,
  updateCurrentParkingCost,
  addNewBooking,
  removeBooking,
} from "@/store/slices/bookingSlice";
import type {
  Booking,
  BookingStatus,
  PaymentStatus,
} from "@/store/slices/bookingSlice";
import type {
  DjangoPaginatedResponse,
  PaginationParams,
} from "@/services/api/axios.client";
import type {
  CreateBookingRequest,
  CreateBookingResponse,
} from "@/services/api/booking.api";

// =====================
// Types
// =====================

export interface BookingFilters {
  status?: BookingStatus;
  paymentStatus?: PaymentStatus;
  vehicleType?: "Car" | "Motorbike";
  startDate?: string;
  endDate?: string;
  page?: number;
  pageSize?: number;
}

export interface BookingResult {
  success: boolean;
  booking?: Booking;
  paymentUrl?: string;
  qrCode?: string;
  message: string;
}

export interface CheckInOutResult {
  success: boolean;
  booking?: Booking;
  totalAmount?: number;
  duration?: number;
  message: string;
}

// Re-export types for consumers
export type PackagePricing = PackagePricingResponse;
export type RevenueSummary = ApiRevenueSummary;
export type DailyRevenueItem = ApiDailyRevenueItem;
export type HourlyRevenueItem = ApiHourlyRevenueItem;

interface ApiErrorPayload {
  response?: {
    data?: {
      message?: string;
    };
  };
}

const getApiErrorMessage = (
  error: unknown,
  fallbackMessage: string,
): string => {
  const apiError = error as ApiErrorPayload;
  return apiError.response?.data?.message || fallbackMessage;
};

// =====================
// Booking Business Service
// =====================

export const bookingService = {
  /**
   * Get booking history with filters
   */
  async getHistory(
    filters?: BookingFilters,
  ): Promise<DjangoPaginatedResponse<Booking>> {
    const response = await bookingApi.getBookings({
      page: filters?.page,
      pageSize: filters?.pageSize,
      status: filters?.status,
      payment_status: filters?.paymentStatus,
      vehicle_type: filters?.vehicleType,
      start_date: filters?.startDate,
      end_date: filters?.endDate,
    });
    return response;
  },

  /**
   * Create new booking
   * - Validates user's no-show status
   * - Creates booking
   * - Subscribes to realtime updates
   */
  async createBooking(data: CreateBookingRequest): Promise<BookingResult> {
    try {
      const response = await bookingApi.createBooking(data);

      // Subscribe to booking updates
      websocketService.subscribe(`booking.${response.booking.id}`);

      // Add to Redux state
      store.dispatch(addNewBooking(response.booking));

      return {
        success: true,
        booking: response.booking,
        paymentUrl: response.paymentUrl,
        qrCode: response.qrCode,
        message: response.message,
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Không thể tạo booking"),
      };
    }
  },

  /**
   * Cancel booking
   * - Only allowed if not checked in
   */
  async cancelBooking(
    bookingId: string,
    reason?: string,
  ): Promise<BookingResult> {
    try {
      await bookingApi.cancelBooking(bookingId, reason);

      // Unsubscribe from booking updates
      websocketService.unsubscribe(`booking.${bookingId}`);

      // Update Redux state
      store.dispatch(updateBookingStatus({ bookingId, status: "cancelled" }));

      return {
        success: true,
        message: "Đã hủy đặt chỗ thành công",
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Không thể hủy booking"),
      };
    }
  },

  /**
   * Check in to parking
   */
  async checkIn(
    bookingId: string,
    licensePlate?: string,
  ): Promise<CheckInOutResult> {
    try {
      const response = await bookingApi.checkIn({
        bookingId: bookingId,
        licensePlate: licensePlate,
      });

      store.dispatch(updateBookingStatus({ bookingId, status: "checked_in" }));

      return {
        success: true,
        booking: response.booking,
        message: response.message,
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Check-in thất bại"),
      };
    }
  },

  /**
   * Check out from parking
   */
  async checkOut(bookingId: string): Promise<CheckInOutResult> {
    try {
      const response = await bookingApi.checkOut({ bookingId: bookingId });

      // Unsubscribe from booking updates
      websocketService.unsubscribe(`booking.${bookingId}`);

      store.dispatch(updateBookingStatus({ bookingId, status: "checked_out" }));

      return {
        success: true,
        booking: response.booking,
        totalAmount: response.totalAmount,
        duration: response.duration,
        message: response.message,
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Check-out thất bại"),
      };
    }
  },

  /**
   * Get current parking session
   */
  async getCurrentParking() {
    return bookingApi.getCurrentParking();
  },

  /**
   * Get upcoming bookings
   */
  async getUpcoming(): Promise<Booking[]> {
    return bookingApi.getUpcomingBookings();
  },

  /**
   * Get booking statistics
   */
  async getStats() {
    return bookingApi.getBookingStats();
  },

  /**
   * Initiate payment for a booking
   */
  async initiatePayment(
    bookingId: string,
    method: "momo" | "vnpay" | "zalopay" | "credit_card",
  ) {
    const response = await bookingApi.initiatePayment({
      bookingId: bookingId,
      paymentMethod: method,
    });
    return {
      paymentUrl: response.paymentUrl,
      transactionId: response.transactionId,
    };
  },

  /**
   * Verify payment completion
   */
  async verifyPayment(
    transactionId: string,
  ): Promise<{ success: boolean; booking: Booking; message: string }> {
    return bookingApi.verifyPayment(transactionId);
  },

  /**
   * Get QR code for booking
   */
  async getQRCode(
    bookingId: string,
  ): Promise<{ qrCode: string; expiresAt: string }> {
    const response = await bookingApi.getQRCode(bookingId);
    return { qrCode: response.qrCode, expiresAt: response.expiresAt };
  },

  /**
   * Handle realtime booking status update
   * Called by websocketService.processMessage
   */
  handleBookingUpdate(data: {
    bookingId: string;
    status: BookingStatus;
    paymentStatus?: PaymentStatus;
  }): void {
    store.dispatch(updateBookingStatus(data));
  },

  /**
   * Handle realtime cost update for current parking
   */
  handleCostUpdate(data: { currentCost: number; duration: number }): void {
    store.dispatch(updateCurrentParkingCost(data));
  },

  /**
   * Select a booking for detail view
   */
  selectBooking(booking: Booking | null): void {
    store.dispatch(setSelectedBooking(booking));
  },

  // =====================
  // Package Pricing
  // =====================

  /**
   * Get package pricing from booking-service
   */
  async getPackagePricing(): Promise<PackagePricing[]> {
    return bookingApi.getPackagePricing();
  },

  /**
   * Get booking by slot ID (for slot verification)
   */
  async getBookingBySlot(slotId: string): Promise<Booking | null> {
    return bookingApi.getBookingBySlot(slotId);
  },

  /**
   * Poll payment status for a booking
   */
  async pollPaymentStatus(
    bookingId: string,
  ): Promise<{ paymentStatus: string; booking: Booking }> {
    return bookingApi.pollPaymentStatus(bookingId);
  },

  /**
   * Extend an active booking's duration
   */
  async extendBooking(
    bookingId: string,
    additionalHours: number,
  ): Promise<ExtendBookingResponse> {
    return bookingApi.extendBooking({ bookingId, additionalHours });
  },

  // =====================
  // Revenue Admin
  // =====================

  /**
   * Get revenue summary (admin)
   */
  async getRevenueSummary(): Promise<RevenueSummary> {
    return bookingApi.getRevenueSummary();
  },

  /**
   * Get daily revenue data (admin)
   */
  async getDailyRevenue(days?: number): Promise<DailyRevenueItem[]> {
    return bookingApi.getDailyRevenue(days);
  },

  /**
   * Get hourly revenue data (admin)
   */
  async getHourlyRevenue(date?: string): Promise<HourlyRevenueItem[]> {
    return bookingApi.getHourlyRevenue(date);
  },

  // =====================
  // Raw API Wrappers (for Store Thunks)
  // These methods just call API without Redux side effects,
  // allowing thunks to handle state updates via extraReducers.
  // =====================

  /**
   * Get bookings (raw API call)
   * For use by Redux async thunks
   */
  async getBookingsRaw(params?: {
    page?: number;
    status?: string;
    paymentStatus?: string;
    vehicleType?: "Car" | "Motorbike";
    startDate?: string;
    endDate?: string;
  }): Promise<DjangoPaginatedResponse<Booking>> {
    return bookingApi.getBookings({
      page: params?.page,
      status: params?.status,
      payment_status: params?.paymentStatus,
      vehicle_type: params?.vehicleType,
      start_date: params?.startDate,
      end_date: params?.endDate,
    });
  },

  /**
   * Get current parking (raw API call)
   * For use by Redux async thunks
   */
  async getCurrentParkingRaw(): Promise<{
    booking: Booking;
    duration: number;
    currentCost: number;
  } | null> {
    return bookingApi.getCurrentParking();
  },

  /**
   * Create booking (raw API call)
   * For use by Redux async thunks
   */
  async createBookingRaw(data: CreateBookingRequest): Promise<CreateBookingResponse> {
    return bookingApi.createBooking(data);
  },

  /**
   * Cancel booking (raw API call)
   * For use by Redux async thunks
   */
  async cancelBookingRaw(bookingId: string, reason?: string): Promise<void> {
    return bookingApi.cancelBooking(bookingId, reason);
  },
};
