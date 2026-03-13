/**
 * Booking Slice
 * Manages booking state with realtime status updates
 */

import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { bookingApi } from "@/services/api/booking.api";

export type BookingStatus =
  | "pending" // Chờ thanh toán
  | "confirmed" // Đã xác nhận
  | "cancelled" // Đã hủy
  | "expired"; // Hết hạn

export type CheckInStatus =
  | "not_checked_in"
  | "checked_in"
  | "checked_out"
  | "cancelled"
  | "no_show";

export type PaymentStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "refunded"
  | "cancelled";

export interface Booking {
  id: string;
  userId: string;
  slotId: string;
  slotCode: string;
  zoneId: string;
  zoneName: string;
  lotId: string;
  lotName: string;
  vehicleId: string;
  licensePlate: string;
  vehicleType: "Car" | "Motorbike";
  packageType?: "hourly" | "daily" | "weekly" | "monthly";
  startTime: string;
  endTime?: string;
  checkInTime?: string;
  checkOutTime?: string;
  bookingStatus: BookingStatus;
  checkInStatus: CheckInStatus;
  status: BookingStatus; // Alias for backward compat
  paymentStatus: PaymentStatus;
  price: number;
  totalAmount: number; // Alias for backward compat
  createdAt: string;
  updatedAt: string;
}

export interface CurrentParking {
  booking: Booking;
  duration: number; // in minutes
  currentCost: number; // Frontend uses camelCase
}

// Type for backend API response (mixed case support)
interface BookingApiResponse {
  id?: string;
  booking_id?: string;
  userId?: string;
  user_id?: string;
  slotId?: string;
  slot_id?: string;
  carSlot?: { id?: string; code?: string };
  car_slot?: { id?: string; code?: string };
  slot?: { code?: string };
  slotCode?: string;
  slot_code?: string;
  zoneId?: string;
  zone_id?: string;
  zone?: { id?: string; name?: string };
  zoneName?: string;
  zone_name?: string;
  lotId?: string;
  lot_id?: string;
  parkingLot?: { id?: string; name?: string };
  parking_lot?: { id?: string; name?: string };
  lotName?: string;
  lot_name?: string;
  vehicleId?: string;
  vehicle_id?: string;
  vehicle?: {
    id?: string;
    licensePlate?: string;
    license_plate?: string;
    vehicleType?: string;
    vehicle_type?: string;
  };
  licensePlate?: string;
  license_plate?: string;
  vehicleType?: string;
  vehicle_type?: string;
  startTime?: string;
  start_time?: string;
  endTime?: string;
  end_time?: string;
  checkInTime?: string;
  checkedInAt?: string;
  checked_in_at?: string;
  checkOutTime?: string;
  checkedOutAt?: string;
  checked_out_at?: string;
  status?: string;
  bookingStatus?: string;
  booking_status?: string;
  checkInStatus?: string;
  check_in_status?: string;
  paymentStatus?: string;
  payment_status?: string;
  totalAmount?: string | number;
  total_amount?: string | number;
  price?: string | number;
  packageType?: string;
  package_type?: string;
  createdAt?: string;
  created_at?: string;
  updatedAt?: string;
  updated_at?: string;
}

// Helper to convert API response to frontend format
export function mapCurrentParkingResponse(response: {
  booking: BookingApiResponse;
  duration: number;
  currentCost?: number; // New camelCase format
  current_cost?: number; // Old snake_case format (backward compatible)
}): CurrentParking {
  return {
    booking: mapBookingResponse(response.booking),
    duration: response.duration,
    currentCost: response.currentCost ?? response.current_cost ?? 0,
  };
}

export function mapBookingResponse(data: BookingApiResponse): Booking {
  // Normalize vehicle type: car -> Car, motorbike -> Motorbike
  let vehicleType: string | undefined =
    data.vehicleType ||
    data.vehicle?.vehicleType ||
    data.vehicle?.vehicle_type ||
    data.vehicle_type;
  if (vehicleType) {
    const vt = vehicleType.toLowerCase();
    if (vt === "car") {
      vehicleType = "Car";
    } else if (vt === "motorbike" || vt === "motorcycle" || vt === "bike") {
      vehicleType = "Motorbike";
    }
  }

  return {
    id: (data.id || data.booking_id || "") as string,
    userId: (data.userId || data.user_id || "") as string,
    slotId: (data.slotId ||
      data.carSlot?.id ||
      data.car_slot?.id ||
      data.slot_id ||
      "") as string,
    slotCode: (data.slotCode ||
      data.carSlot?.code ||
      data.car_slot?.code ||
      data.slot?.code ||
      data.slot_code ||
      "") as string,
    zoneId: (data.zoneId || data.zone?.id || data.zone_id || "") as string,
    zoneName: (data.zoneName ||
      data.zone?.name ||
      data.zone_name ||
      "") as string,
    lotId: (data.lotId ||
      data.parkingLot?.id ||
      data.parking_lot?.id ||
      data.lot_id ||
      "") as string,
    lotName: (data.lotName ||
      data.parkingLot?.name ||
      data.parking_lot?.name ||
      data.lot_name ||
      "") as string,
    vehicleId: (data.vehicleId ||
      data.vehicle?.id ||
      data.vehicle_id ||
      "") as string,
    licensePlate: (data.licensePlate ||
      data.vehicle?.licensePlate ||
      data.vehicle?.license_plate ||
      data.license_plate ||
      "") as string,
    vehicleType: (vehicleType || "Car") as "Car" | "Motorbike",
    packageType: (data.packageType || data.package_type) as
      | "hourly"
      | "daily"
      | "weekly"
      | "monthly"
      | undefined,
    startTime: (data.startTime || data.start_time || "") as string,
    endTime: data.endTime || data.end_time,
    checkInTime: data.checkInTime || data.checkedInAt || data.checked_in_at,
    checkOutTime: data.checkOutTime || data.checkedOutAt || data.checked_out_at,
    status: (data.bookingStatus ||
      data.booking_status ||
      data.status ||
      "pending") as BookingStatus,
    bookingStatus: (data.bookingStatus ||
      data.booking_status ||
      data.status ||
      "pending") as BookingStatus,
    checkInStatus: (data.checkInStatus ||
      data.check_in_status ||
      "not_checked_in") as CheckInStatus,
    paymentStatus: (data.paymentStatus ||
      data.payment_status ||
      "pending") as PaymentStatus,
    price: parseFloat(
      String(data.totalAmount || data.total_amount || data.price || 0),
    ),
    totalAmount: parseFloat(
      String(data.totalAmount || data.total_amount || data.price || 0),
    ),
    createdAt: (data.createdAt || data.created_at || "") as string,
    updatedAt: (data.updatedAt || data.updated_at || "") as string,
  };
}

interface BookingState {
  bookings: Booking[];
  currentParking: CurrentParking | null;
  upcomingBookings: Booking[];
  selectedBooking: Booking | null;
  isLoading: boolean;
  error: string | null;
  // Pagination (Django REST format)
  pagination: {
    count: number;
    next: string | null;
    previous: string | null;
  };
}

const initialState: BookingState = {
  bookings: [],
  currentParking: null,
  upcomingBookings: [],
  selectedBooking: null,
  isLoading: false,
  error: null,
  pagination: {
    count: 0,
    next: null,
    previous: null,
  },
};

// Async thunks
export const fetchBookings = createAsyncThunk(
  "booking/fetchBookings",
  async (
    params: { page?: number; status?: BookingStatus } | undefined,
    { rejectWithValue },
  ) => {
    try {
      const response = await bookingApi.getBookings(params);
      return {
        results: response.results.map((item: BookingApiResponse) =>
          mapBookingResponse(item),
        ),
        count: response.count,
        next: response.next,
        previous: response.previous,
      };
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } };
      return rejectWithValue(
        err.response?.data?.message || "Không thể tải thông tin xe đang đậu",
      );
    }
  },
);

export const fetchCurrentParking = createAsyncThunk(
  "booking/fetchCurrentParking",
  async (_, { rejectWithValue }) => {
    try {
      const response = await bookingApi.getCurrentParking();
      if (!response) return null;
      return mapCurrentParkingResponse(response);
    } catch (error: unknown) {
      const err = error as {
        response?: { status?: number; data?: { message?: string } };
      };
      // If no current parking, return null instead of error
      if (err.response?.status === 404) {
        return null;
      }
      return rejectWithValue(
        err.response?.data?.message || "Không thể tải thông tin đỗ xe hiện tại",
      );
    }
  },
);

export const createBooking = createAsyncThunk(
  "booking/createBooking",
  async (
    data: {
      vehicleId: string;
      slotId?: string | null;
      zoneId: string;
      parkingLotId: string;
      startTime: string;
      endTime?: string;
      packageType?: "hourly" | "daily" | "weekly" | "monthly";
      paymentMethod: "online" | "on_exit";
    },
    { rejectWithValue },
  ) => {
    try {
      const response = await bookingApi.createBooking(data);
      return {
        booking: mapBookingResponse(response.booking as BookingApiResponse),
        paymentUrl: response.paymentUrl,
        qrCode: response.qrCode,
        message: response.message,
      };
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } };
      return rejectWithValue(
        err.response?.data?.message || "Failed to create booking",
      );
    }
  },
);

export const cancelBooking = createAsyncThunk(
  "booking/cancelBooking",
  async (bookingId: string, { rejectWithValue }) => {
    try {
      await bookingApi.cancelBooking(bookingId);
      return bookingId;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } };
      return rejectWithValue(
        err.response?.data?.message || "Không thể hủy booking",
      );
    }
  },
);

const bookingSlice = createSlice({
  name: "booking",
  initialState,
  reducers: {
    setSelectedBooking: (state, action: PayloadAction<Booking | null>) => {
      state.selectedBooking = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    // Realtime updates from WebSocket
    updateBookingStatus: (
      state,
      action: PayloadAction<{
        bookingId: string;
        status: BookingStatus;
        paymentStatus?: PaymentStatus;
      }>,
    ) => {
      const booking = state.bookings.find(
        (b) => b.id === action.payload.bookingId,
      );
      if (booking) {
        booking.status = action.payload.status;
        if (action.payload.paymentStatus) {
          booking.paymentStatus = action.payload.paymentStatus;
        }
        booking.updatedAt = new Date().toISOString();
      }

      // Update current parking if it's the same booking
      if (state.currentParking?.booking.id === action.payload.bookingId) {
        state.currentParking.booking.status = action.payload.status;
        if (action.payload.paymentStatus) {
          state.currentParking.booking.paymentStatus =
            action.payload.paymentStatus;
        }
      }
    },
    updateCurrentParkingCost: (
      state,
      action: PayloadAction<{ duration: number; currentCost: number }>,
    ) => {
      if (state.currentParking) {
        state.currentParking.duration = action.payload.duration;
        state.currentParking.currentCost = action.payload.currentCost;
      }
    },
    addNewBooking: (state, action: PayloadAction<Booking>) => {
      state.bookings.unshift(action.payload);
      state.pagination.count += 1;
    },
    removeBooking: (state, action: PayloadAction<string>) => {
      state.bookings = state.bookings.filter((b) => b.id !== action.payload);
      state.pagination.count -= 1;
    },
  },
  extraReducers: (builder) => {
    // Fetch bookings
    builder
      .addCase(fetchBookings.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchBookings.fulfilled, (state, action) => {
        state.isLoading = false;
        state.bookings = action.payload.results;
        state.pagination = {
          count: action.payload.count,
          next: action.payload.next,
          previous: action.payload.previous,
        };
      })
      .addCase(fetchBookings.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Fetch current parking
    builder
      .addCase(fetchCurrentParking.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(fetchCurrentParking.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentParking = action.payload;
      })
      .addCase(fetchCurrentParking.rejected, (state, action) => {
        state.isLoading = false;
        state.currentParking = null;
      });

    // Create booking
    builder
      .addCase(createBooking.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(createBooking.fulfilled, (state, action) => {
        state.isLoading = false;
        state.bookings.unshift(action.payload.booking);
        state.selectedBooking = action.payload.booking;
      })
      .addCase(createBooking.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Cancel booking
    builder
      .addCase(cancelBooking.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(cancelBooking.fulfilled, (state, action) => {
        state.isLoading = false;
        const booking = state.bookings.find((b) => b.id === action.payload);
        if (booking) {
          booking.status = "cancelled";
        }
      })
      .addCase(cancelBooking.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const {
  setSelectedBooking,
  clearError,
  updateBookingStatus,
  updateCurrentParkingCost,
  addNewBooking,
  removeBooking,
} = bookingSlice.actions;

export default bookingSlice.reducer;
