/**
 * useBooking Hook
 * Provides booking-related functionality using Redux store
 */

import { useCallback } from "react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  fetchBookings,
  fetchCurrentParking,
  createBooking,
  cancelBooking,
  setSelectedBooking,
  clearError,
  updateBookingStatus,
} from "@/store/slices/bookingSlice";
import { bookingApi } from "@/services/api/booking.api";
import type { Booking, BookingStatus } from "@/store/slices/bookingSlice";

interface CreateBookingParams {
  vehicleId: string;
  slotId?: string | null;
  zoneId: string;
  parkingLotId: string;
  startTime: string;
  endTime?: string | null;
  packageType?: "hourly" | "daily" | "weekly" | "monthly";
  paymentMethod: "online" | "on_exit";
}

export function useBooking() {
  const dispatch = useAppDispatch();

  const {
    bookings,
    currentParking,
    upcomingBookings,
    selectedBooking,
    isLoading,
    error,
    pagination,
  } = useAppSelector((state) => state.booking);

  // Fetch booking history
  const loadBookings = useCallback(
    (params?: { page?: number; status?: BookingStatus }) => {
      return dispatch(fetchBookings(params));
    },
    [dispatch],
  );

  // Fetch current parking session
  const loadCurrentParking = useCallback(() => {
    return dispatch(fetchCurrentParking());
  }, [dispatch]);

  // Create new booking
  const create = useCallback(
    (params: CreateBookingParams) => {
      return dispatch(createBooking(params));
    },
    [dispatch],
  );

  // Cancel booking
  const cancel = useCallback(
    (bookingId: string) => {
      return dispatch(cancelBooking(bookingId));
    },
    [dispatch],
  );

  // Select booking for viewing details
  const selectBooking = useCallback(
    (booking: Booking | null) => {
      dispatch(setSelectedBooking(booking));
    },
    [dispatch],
  );

  // Clear booking error
  const clearBookingError = useCallback(() => {
    dispatch(clearError());
  }, [dispatch]);

  // Filter bookings by status
  const getBookingsByStatus = useCallback(
    (status: BookingStatus) => {
      return bookings.filter((booking) => booking.status === status);
    },
    [bookings],
  );

  // Get active bookings (not cancelled, not completed)
  const activeBookings = bookings.filter(
    (booking) =>
      booking.status !== "cancelled" &&
      booking.status !== "completed" &&
      booking.status !== "no_show",
  );

  // Get upcoming bookings (confirmed but not checked in)
  const upcoming = bookings.filter(
    (booking) => booking.status === "confirmed" || booking.status === "pending",
  );

  // Get parked bookings
  const parkedBookings = bookings.filter(
    (booking) => booking.status === "parked" || booking.status === "checked_in",
  );

  // Count no-shows
  const noShowCount = bookings.filter(
    (booking) => booking.status === "no_show",
  ).length;

  // Calculate total spent
  const totalSpent = bookings
    .filter((booking) => booking.paymentStatus === "completed")
    .reduce((sum, booking) => sum + booking.totalAmount, 0);

  // Check if user must pay online (2+ no-shows)
  const forceOnlinePayment = noShowCount >= 2;

  // Get booking stats from API
  const getBookingStats = useCallback(async () => {
    try {
      const stats = await bookingApi.getBookingStats();
      return stats;
    } catch (error) {
      console.error("Failed to get booking stats:", error);
      return null;
    }
  }, []);

  // Get upcoming bookings from API
  const getUpcomingBookings = useCallback(async () => {
    try {
      const bookings = await bookingApi.getUpcomingBookings();
      return bookings;
    } catch (error) {
      console.error("Failed to get upcoming bookings:", error);
      return [];
    }
  }, []);

  return {
    // State
    bookings,
    currentParking,
    upcomingBookings,
    selectedBooking,
    isLoading,
    error,
    pagination,

    // Derived state
    activeBookings,
    upcoming,
    parkedBookings,
    noShowCount,
    totalSpent,
    forceOnlinePayment,

    // Actions
    loadBookings,
    loadCurrentParking,
    create,
    cancel,
    selectBooking,
    clearError: clearBookingError,

    // API methods
    getBookingStats,
    getUpcomingBookings,

    // Helpers
    getBookingsByStatus,
  };
}
