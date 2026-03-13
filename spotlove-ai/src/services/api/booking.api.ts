/**
 * Booking API Service
 * API calls for booking management with Django REST pagination
 */

import apiClient, {
  buildPaginationParams,
  type DjangoPaginatedResponse,
  type PaginationParams,
} from "./axios.client";
import type {
  Booking,
  BookingStatus,
  PaymentStatus,
} from "@/store/slices/bookingSlice";

// =====================
// Types
// =====================

export interface GetBookingsParams extends PaginationParams {
  status?: BookingStatus;
  payment_status?: PaymentStatus;
  vehicle_type?: "Car" | "Motorbike";
  start_date?: string;
  end_date?: string;
}

export interface CreateBookingRequest {
  vehicleId: string;
  slotId?: string | null;
  zoneId: string;
  parkingLotId: string;
  startTime: string;
  endTime?: string;
  packageType?: "hourly" | "daily" | "weekly" | "monthly";
  paymentMethod: "online" | "on_exit";
}

export interface CreateBookingResponse {
  booking: Booking;
  paymentUrl?: string; // If online payment
  qrCode?: string; // QR code for check-in
  message: string;
}

export interface CheckInRequest {
  bookingId: string;
  licensePlate?: string; // For verification
}

export interface CheckOutRequest {
  bookingId: string;
}

export interface PaymentRequest {
  bookingId: string;
  paymentMethod: "momo" | "vnpay" | "zalopay" | "credit_card";
}

export interface PaymentResponse {
  paymentUrl: string;
  transactionId: string;
}

export interface PackagePricingResponse {
  id: string;
  packageType: "hourly" | "daily" | "weekly" | "monthly";
  vehicleType: "Car" | "Motorbike";
  price: number;
  description?: string;
}

// ── Revenue Admin Types ──────────────────────────────────────────────────

export interface RevenueSummary {
  totalRevenue: number;
  todayRevenue: number;
  thisWeekRevenue: number;
  thisMonthRevenue: number;
  totalBookings: number;
  completedBookings: number;
  cancelledBookings: number;
  activeBookings: number;
  averageBookingValue: number;
  paymentMethods: {
    online?: { count: number; amount: number };
    onExit?: { count: number; amount: number };
    [key: string]: { count: number; amount: number } | undefined;
  };
}

export interface DailyRevenueItem {
  date: string;
  revenue: number;
  bookings: number;
}

export interface HourlyRevenueItem {
  hour: number;
  revenue: number;
  bookings: number;
}

// =====================
// API Endpoints
// =====================

export const bookingApi = {
  /**
   * Get list of bookings with pagination
   */
  getBookings: async (
    params?: GetBookingsParams,
  ): Promise<DjangoPaginatedResponse<Booking>> => {
    const queryParams: Record<string, string> = {};

    if (params) {
      Object.assign(queryParams, buildPaginationParams(params));
      if (params.status) queryParams.status = params.status;
      if (params.payment_status)
        queryParams.payment_status = params.payment_status;
      if (params.vehicle_type) queryParams.vehicle_type = params.vehicle_type;
      if (params.start_date) queryParams.start_date = params.start_date;
      if (params.end_date) queryParams.end_date = params.end_date;
    }

    const response = await apiClient.get<DjangoPaginatedResponse<Booking>>(
      "/bookings/",
      { params: queryParams },
    );
    return response.data;
  },

  /**
   * Get single booking details
   */
  getBooking: async (bookingId: string): Promise<Booking> => {
    const response = await apiClient.get<Booking>(`/bookings/${bookingId}/`);
    return response.data;
  },

  /**
   * Create new booking
   */
  createBooking: async (
    data: CreateBookingRequest,
  ): Promise<CreateBookingResponse> => {
    // CamelCaseJSONParser on Django side converts camelCase → snake_case automatically
    const response = await apiClient.post<CreateBookingResponse>(
      "/bookings/",
      data,
    );
    return response.data;
  },

  /**
   * Cancel booking
   */
  cancelBooking: async (bookingId: string, reason?: string): Promise<void> => {
    await apiClient.post(`/bookings/${bookingId}/cancel/`, { reason });
  },

  /**
   * Get current active parking session
   * Backend returns camelCase due to CamelCaseJSONRenderer
   */
  getCurrentParking: async (): Promise<{
    booking: Booking;
    duration: number;
    currentCost: number; // camelCase from backend
    message?: string;
  } | null> => {
    const response = await apiClient.get("/bookings/current-parking/");
    return response.data;
  },

  /**
   * Check-in to parking
   */
  checkIn: async (
    data: CheckInRequest,
  ): Promise<{
    booking: Booking;
    message: string;
  }> => {
    const response = await apiClient.post(
      `/bookings/${data.bookingId}/checkin/`,
      data,
    );
    return response.data;
  },

  /**
   * Check-out from parking
   */
  checkOut: async (
    data: CheckOutRequest,
  ): Promise<{
    booking: Booking;
    totalAmount: number;
    duration: number;
    message: string;
  }> => {
    const response = await apiClient.post(
      `/bookings/${data.bookingId}/checkout/`,
      data,
    );
    return response.data;
  },

  /**
   * Get booking history with stats
   */
  getBookingStats: async (): Promise<{
    totalBookings: number;
    totalSpent: number;
    totalHours: number;
    noShowCount: number;
    favoriteLot?: string;
    monthlyExpenses?: Array<{ month: string; amount: number }>;
  }> => {
    const response = await apiClient.get("/bookings/stats/");
    return response.data;
  },

  /**
   * Get upcoming bookings
   */
  getUpcomingBookings: async (): Promise<Booking[]> => {
    const response = await apiClient.get<DjangoPaginatedResponse<Booking>>(
      "/bookings/",
      {
        params: {
          booking_status: "confirmed",
          check_in_status: "not_checked_in",
          ordering: "start_time",
          page_size: 5,
        },
      },
    );
    return response.data.results;
  },

  /**
   * Initiate payment for a booking
   */
  initiatePayment: async (data: PaymentRequest): Promise<PaymentResponse> => {
    const response = await apiClient.post<PaymentResponse>(
      "/bookings/payment/",
      data,
    );
    return response.data;
  },

  /**
   * Verify payment callback
   */
  verifyPayment: async (
    transactionId: string,
  ): Promise<{
    success: boolean;
    booking: Booking;
    message: string;
  }> => {
    const response = await apiClient.post("/bookings/payment/verify/", {
      transactionId: transactionId,
    });
    return response.data;
  },

  /**
   * Get QR code for booking
   */
  getQRCode: async (
    bookingId: string,
  ): Promise<{
    qrCode: string;
    expiresAt: string;
  }> => {
    const response = await apiClient.get(`/bookings/${bookingId}/qr-code/`);
    return response.data;
  },

  /**
   * Get package pricing from booking-service.
   * Replaces hardcoded prices in PriceSummary.
   */
  getPackagePricing: async (): Promise<PackagePricingResponse[]> => {
    const response = await apiClient.get<
      DjangoPaginatedResponse<PackagePricingResponse>
    >("/bookings/packagepricings/");
    return response.data.results;
  },

  /**
   * Get booking by slot ID (for slot verification).
   */
  getBookingBySlot: async (slotId: string): Promise<Booking | null> => {
    const response = await apiClient.get<DjangoPaginatedResponse<Booking>>(
      "/bookings/",
      {
        params: {
          slot_id: slotId,
          check_in_status: "checked_in",
          page_size: 1,
        },
      },
    );
    return response.data.results[0] || null;
  },

  /**
   * Poll payment status for a booking.
   */
  pollPaymentStatus: async (
    bookingId: string,
  ): Promise<{
    paymentStatus: string;
    booking: Booking;
  }> => {
    const response = await apiClient.get(`/bookings/${bookingId}/`);
    const booking = response.data;
    return {
      paymentStatus:
        booking.paymentStatus || booking.payment_status || "pending",
      booking,
    };
  },

  // ========== Revenue Admin ==========

  /**
   * Get revenue summary (admin)
   */
  getRevenueSummary: async (): Promise<RevenueSummary> => {
    const response = await apiClient.get<RevenueSummary>(
      "/bookings/admin/revenue/summary/",
    );
    return response.data;
  },

  /**
   * Get daily revenue data (admin)
   */
  getDailyRevenue: async (days?: number): Promise<DailyRevenueItem[]> => {
    const response = await apiClient.get<{ data: DailyRevenueItem[] }>(
      "/bookings/admin/revenue/daily/",
      { params: days ? { days } : undefined },
    );
    return response.data.data;
  },

  /**
   * Get hourly revenue data (admin)
   */
  getHourlyRevenue: async (date?: string): Promise<HourlyRevenueItem[]> => {
    const response = await apiClient.get<{ data: HourlyRevenueItem[] }>(
      "/bookings/admin/revenue/hourly/",
      { params: date ? { date } : undefined },
    );
    return response.data.data;
  },
};
