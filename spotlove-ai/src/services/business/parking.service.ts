/**
 * Parking Business Service
 * Business logic layer - handles parking operations + realtime
 *
 * Pattern: service.ts = Business Logic + Redux + WebSocket Integration
 *          api.ts = Pure HTTP calls only
 */

import { parkingApi } from "@/services/api/parking.api";
import type { Floor as ApiFloor } from "@/services/api/parking.api";
import { websocketService, WSMessageType } from "@/services/websocket.service";
import { store } from "@/store";
import {
  setSelectedLot,
  setSelectedZone,
  updateSlotStatus,
  updateZoneAvailability,
  updateLotAvailability,
  batchUpdateSlots,
} from "@/store/slices/parkingSlice";
import type { ParkingZone, ParkingSlot } from "@/store/slices/parkingSlice";
import type { ParkingLot } from "@/types/parking";
import type {
  DjangoPaginatedResponse,
  PaginationParams,
} from "@/services/api/axios.client";

// =====================
// Types
// =====================

export interface SearchParkingParams {
  lat?: number;
  lng?: number;
  radius?: number;
  vehicleType?: "Car" | "Motorbike";
  page?: number;
  pageSize?: number;
}

export interface SlotAvailabilityCheck {
  slotId: string;
  startTime: string;
  endTime?: string;
}

// Re-export Floor type for consumers
export type Floor = ApiFloor;

// =====================
// Parking Business Service
// =====================

export const parkingService = {
  /**
   * Get parking lots with optional filters
   */
  async getLots(params?: {
    lat?: number;
    lng?: number;
    radius?: number;
    vehicleType?: "Car" | "Motorbike";
    isOpen?: boolean;
    page?: number;
    pageSize?: number;
  }): Promise<DjangoPaginatedResponse<ParkingLot>> {
    return parkingApi.getLots({
      lat: params?.lat,
      lng: params?.lng,
      radius: params?.radius,
      vehicle_type: params?.vehicleType,
      is_open: params?.isOpen,
      page: params?.page,
      pageSize: params?.pageSize,
    });
  },

  /**
   * Get single parking lot details
   */
  async getLot(lotId: string): Promise<ParkingLot> {
    return parkingApi.getLot(lotId);
  },

  /**
   * Get nearest parking lots based on user location
   */
  async getNearestLots(params: {
    lat: number;
    lng: number;
    vehicleType?: "Car" | "Motorbike";
    limit?: number;
  }): Promise<DjangoPaginatedResponse<ParkingLot & { distance?: number; availableSlots?: number }>> {
    return parkingApi.getNearestLots(params);
  },

  /**
   * Get floors for a parking lot
   */
  async getFloors(
    lotId: string,
    params?: { page?: number; pageSize?: number },
  ): Promise<DjangoPaginatedResponse<Floor>> {
    return parkingApi.getFloors({
      lot_id: lotId,
      page: params?.page,
      pageSize: params?.pageSize,
    });
  },

  /**
   * Get zones with filters
   */
  async getZones(params: {
    lotId: string;
    floor?: number;
    vehicleType?: "Car" | "Motorbike";
    page?: number;
    pageSize?: number;
  }): Promise<DjangoPaginatedResponse<ParkingZone>> {
    return parkingApi.getZones({
      lot_id: params.lotId,
      floor: params.floor,
      vehicle_type: params.vehicleType,
      page: params.page,
      pageSize: params.pageSize,
    }) as Promise<DjangoPaginatedResponse<ParkingZone>>;
  },

  /**
   * Get slots with filters
   */
  async getSlots(params?: {
    zoneId?: string;
    status?: "available" | "occupied" | "reserved" | "maintenance";
    page?: number;
    pageSize?: number;
  }): Promise<DjangoPaginatedResponse<ParkingSlot>> {
    return parkingApi.getSlots({
      zone_id: params?.zoneId,
      status: params?.status,
      page: params?.page,
      pageSize: params?.pageSize,
    }) as Promise<DjangoPaginatedResponse<ParkingSlot>>;
  },

  /**
   * Search parking lots near location
   * - Calls API
   * - Returns results (Redux update via hook/thunk)
   */
  async searchNearby(
    params: SearchParkingParams,
  ): Promise<DjangoPaginatedResponse<ParkingLot>> {
    const response = await parkingApi.getLots({
      lat: params.lat,
      lng: params.lng,
      radius: params.radius,
      vehicle_type: params.vehicleType,
      page: params.page,
      pageSize: params.pageSize,
    });
    return response;
  },

  /**
   * Get zones for a parking lot
   */
  async getZonesForLot(
    lotId: string,
    floor?: number,
    vehicleType?: "Car" | "Motorbike",
  ): Promise<ParkingZone[]> {
    const response = await parkingApi.getZones({
      lot_id: lotId,
      floor,
      vehicle_type: vehicleType,
    });
    return response.results as unknown as ParkingZone[];
  },

  /**
   * Get slots for a zone + subscribe to realtime
   */
  async getSlotsForZone(zoneId: string): Promise<ParkingSlot[]> {
    const response = await parkingApi.getSlots({ zone_id: zoneId });

    // Subscribe to realtime updates for this zone
    websocketService.subscribe(`parking.zone.${zoneId}`);

    return response.results as unknown as ParkingSlot[];
  },

  /**
   * Check slot availability before booking
   */
  async checkAvailability(params: SlotAvailabilityCheck): Promise<boolean> {
    const response = await parkingApi.checkAvailability({
      slotId: params.slotId,
      startTime: params.startTime,
      endTime: params.endTime,
    });
    return response.isAvailable;
  },

  /**
   * Select a parking lot (updates Redux + subscribes to realtime)
   */
  selectLot(lot: ParkingLot | null): void {
    store.dispatch(setSelectedLot(lot));

    if (lot) {
      websocketService.subscribe(`parking.lot.${lot.id}`);
    }
  },

  /**
   * Unsubscribe from lot updates
   */
  unselectLot(lotId: string): void {
    store.dispatch(setSelectedLot(null));
    websocketService.unsubscribe(`parking.lot.${lotId}`);
  },

  /**
   * Select a zone (updates Redux + subscribes to realtime)
   */
  selectZone(zone: ParkingZone | null): void {
    store.dispatch(setSelectedZone(zone));

    if (zone) {
      websocketService.subscribe(`parking.zone.${zone.id}`);
    }
  },

  /**
   * Unsubscribe from zone updates
   */
  unselectZone(zoneId: string): void {
    store.dispatch(setSelectedZone(null));
    websocketService.unsubscribe(`parking.zone.${zoneId}`);
  },

  /**
   * Handle realtime slot status update from WebSocket
   * Called by websocketService.processMessage
   */
  handleSlotUpdate(data: {
    slotId: string;
    status: ParkingSlot["status"];
    currentVehicle?: ParkingSlot["currentVehicle"];
  }): void {
    store.dispatch(updateSlotStatus(data));
  },

  /**
   * Handle realtime zone availability update
   */
  handleZoneUpdate(data: {
    zoneId: string;
    availableSlots: number;
    occupiedSlots: number;
    reservedSlots: number;
  }): void {
    store.dispatch(updateZoneAvailability(data));
  },

  /**
   * Handle realtime lot availability update
   */
  handleLotUpdate(data: { lotId: string; availableSlots: number }): void {
    store.dispatch(updateLotAvailability(data));
  },

  /**
   * Batch update slots (for initial load or full sync)
   */
  batchUpdateSlots(slots: ParkingSlot[]): void {
    store.dispatch(batchUpdateSlots(slots));
  },

  /**
   * Get current user's geolocation
   */
  async getCurrentLocation(): Promise<{ lat: number; lng: number } | null> {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve(null);
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
        },
        () => {
          resolve(null);
        },
      );
    });
  },
};
