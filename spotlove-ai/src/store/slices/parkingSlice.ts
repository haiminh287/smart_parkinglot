/**
 * Parking Slice
 * Manages parking slots state with realtime updates
 */

import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { parkingService } from "@/services/business";
import { ParkingLot } from "@/types/parking";

export interface ParkingSlot {
  id: string;
  code: string;
  zone: string; // zone UUID
  zoneId?: string; // alias kept for backward compat
  zoneName?: string;
  floor?: number;
  vehicleType?: "Car" | "Motorbike";
  status: "available" | "occupied" | "reserved" | "maintenance";
  camera?: string | null; // camera UUID
  cameraId?: string; // alias
  isAvailable?: boolean;
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
  createdAt?: string;
  updatedAt?: string;
  currentVehicle?: {
    licensePlate: string;
    userId: string;
    checkInTime: string;
  };
}

export interface ParkingZone {
  id: string;
  name: string;
  floor: string; // floor UUID (FK)
  floorId?: string; // alias kept for backward compat
  floorLevel?: number;
  vehicleType: "Car" | "Motorbike";
  capacity: number;
  availableSlots: number;
  occupiedSlots?: number;
  reservedSlots?: number;
  createdAt?: string;
  updatedAt?: string;
}

// export interface ParkingLot {
//   id: string;
//   name: string;
//   address: string;
//   totalSlots: number;
//   availableSlots: number;
//   distance?: number;
//   pricePerHour: number;
//   isOpen: boolean;
// }

interface ParkingState {
  lots: ParkingLot[];
  zones: ParkingZone[];
  slots: ParkingSlot[];
  selectedLot: ParkingLot | null;
  selectedZone: ParkingZone | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: ParkingState = {
  lots: [],
  zones: [],
  slots: [],
  selectedLot: null,
  selectedZone: null,
  isLoading: false,
  error: null,
};

// Async thunks
export const fetchParkingLots = createAsyncThunk(
  "parking/fetchLots",
  async (
    params: { lat?: number; lng?: number } | undefined,
    { rejectWithValue },
  ) => {
    try {
      const response = await parkingService.getLots(params);
      return response.results;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } };
      return rejectWithValue(
        err.response?.data?.message || "Không thể tải danh sách bãi đỗ",
      );
    }
  },
);

export const fetchZones = createAsyncThunk(
  "parking/fetchZones",
  async (lotId: string, { rejectWithValue }) => {
    try {
      const response = await parkingService.getZones({ lotId });
      // Map floorLevel to floor for backward compat
      return response.results.map((zone) => ({
        ...zone,
        floor: zone.floorLevel ?? zone.floor ?? 1,
        floorLevel: zone.floorLevel ?? zone.floor ?? 1,
      }));
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } };
      return rejectWithValue(
        err.response?.data?.message || "Không thể tải danh sách khu vực",
      );
    }
  },
);

export const fetchSlots = createAsyncThunk(
  "parking/fetchSlots",
  async (zoneId: string, { rejectWithValue, getState }) => {
    try {
      const response = await parkingService.getSlots({ zoneId });
      // Enrich slots with zone info from state
      const state = getState() as { parking: ParkingState };
      const zone = state.parking.zones.find((z) => z.id === zoneId);
      return response.results.map((slot) => ({
        ...slot,
        zoneId: slot.zoneId || zoneId,
        zoneName: zone?.name || "",
        floor: zone?.floor ?? zone?.floorLevel ?? 1,
        vehicleType: zone?.vehicleType || "Car",
      }));
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } };
      return rejectWithValue(
        err.response?.data?.message || "Không thể tải danh sách chỗ",
      );
    }
  },
);

const parkingSlice = createSlice({
  name: "parking",
  initialState,
  reducers: {
    setSelectedLot: (state, action: PayloadAction<ParkingLot | null>) => {
      state.selectedLot = action.payload;
    },
    setSelectedZone: (state, action: PayloadAction<ParkingZone | null>) => {
      state.selectedZone = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    // Realtime updates from WebSocket
    updateSlotStatus: (
      state,
      action: PayloadAction<{
        slotId: string;
        status: ParkingSlot["status"];
        currentVehicle?: ParkingSlot["currentVehicle"];
      }>,
    ) => {
      const slot = state.slots.find((s) => s.id === action.payload.slotId);
      if (slot) {
        slot.status = action.payload.status;
        slot.currentVehicle = action.payload.currentVehicle;
      }
    },
    updateZoneAvailability: (
      state,
      action: PayloadAction<{
        zoneId: string;
        availableSlots: number;
        occupiedSlots: number;
        reservedSlots: number;
      }>,
    ) => {
      const zone = state.zones.find((z) => z.id === action.payload.zoneId);
      if (zone) {
        zone.availableSlots = action.payload.availableSlots;
        zone.occupiedSlots = action.payload.occupiedSlots;
        zone.reservedSlots = action.payload.reservedSlots;
      }
    },
    updateLotAvailability: (
      state,
      action: PayloadAction<{ lotId: string; availableSlots: number }>,
    ) => {
      const lot = state.lots.find((l) => l.id === action.payload.lotId);
      if (lot) {
        lot.availableSlots = action.payload.availableSlots;
      }
    },
    // Batch update for efficiency
    batchUpdateSlots: (state, action: PayloadAction<ParkingSlot[]>) => {
      action.payload.forEach((updatedSlot) => {
        const index = state.slots.findIndex((s) => s.id === updatedSlot.id);
        if (index !== -1) {
          state.slots[index] = updatedSlot;
        }
      });
    },
  },
  extraReducers: (builder) => {
    // Fetch lots
    builder
      .addCase(fetchParkingLots.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchParkingLots.fulfilled, (state, action) => {
        state.isLoading = false;
        state.lots = action.payload;
      })
      .addCase(fetchParkingLots.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Fetch zones
    builder
      .addCase(fetchZones.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchZones.fulfilled, (state, action) => {
        state.isLoading = false;
        state.zones = action.payload;
      })
      .addCase(fetchZones.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Fetch slots
    builder
      .addCase(fetchSlots.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchSlots.fulfilled, (state, action) => {
        state.isLoading = false;
        state.slots = action.payload;
      })
      .addCase(fetchSlots.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const {
  setSelectedLot,
  setSelectedZone,
  clearError,
  updateSlotStatus,
  updateZoneAvailability,
  updateLotAvailability,
  batchUpdateSlots,
} = parkingSlice.actions;

export default parkingSlice.reducer;
