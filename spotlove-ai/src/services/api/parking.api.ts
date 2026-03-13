/**
 * Parking API Service
 * API calls for parking lots, zones, and slots with Django REST pagination
 */

import apiClient, {
  buildPaginationParams,
  type DjangoPaginatedResponse,
  type PaginationParams,
} from "./axios.client";
import type { ParkingZone, ParkingSlot } from "@/store/slices/parkingSlice";
import type { ParkingLot } from "@/types/parking";

export interface Floor {
  id: string;
  name: string;
  parkingLot: string; // parking lot UUID (FK)
  level: number;
  zones: ParkingZone[];
  createdAt?: string;
  updatedAt?: string;
}

// =====================
// Types
// =====================

export interface GetLotsParams extends PaginationParams {
  lat?: number;
  lng?: number;
  radius?: number; // in km
  vehicle_type?: "Car" | "Motorbike";
  is_open?: boolean;
}

export interface GetFloorsParams extends PaginationParams {
  lot_id: string;
}

export interface GetZonesParams extends PaginationParams {
  lot_id: string;
  floor?: number;
  vehicle_type?: "Car" | "Motorbike";
}

export interface GetSlotsParams extends PaginationParams {
  zone_id?: string;
  status?: "available" | "occupied" | "reserved" | "maintenance";
}

export interface CheckAvailabilityParams {
  slotId: string;
  startTime: string;
  endTime?: string;
}

export interface CheckAvailabilityResponse {
  isAvailable: boolean;
  conflictBooking?: {
    id: string;
    startTime: string;
    endTime: string;
  };
}

// =====================
// API Endpoints
// =====================

export const parkingApi = {
  /**
   * Get list of parking lots with optional location-based filtering
   */
  getLots: async (
    params?: GetLotsParams,
  ): Promise<DjangoPaginatedResponse<ParkingLot>> => {
    const queryParams: Record<string, string> = {};

    if (params) {
      Object.assign(queryParams, buildPaginationParams(params));
      if (params.lat !== undefined) queryParams.lat = String(params.lat);
      if (params.lng !== undefined) queryParams.lng = String(params.lng);
      if (params.radius) queryParams.radius = String(params.radius);
      if (params.vehicle_type) queryParams.vehicle_type = params.vehicle_type;
      if (params.is_open !== undefined)
        queryParams.is_open = String(params.is_open);
    }

    const response = await apiClient.get<DjangoPaginatedResponse<ParkingLot>>(
      "/parking/lots/",
      { params: queryParams },
    );
    return response.data;
  },

  /**
   * Get single parking lot details
   */
  getLot: async (lotId: string): Promise<ParkingLot> => {
    const response = await apiClient.get<ParkingLot>(`/parking/lots/${lotId}/`);
    return response.data;
  },

  /**
   * Get nearest parking lots based on user location
   */
  getNearestLots: async (params: {
    lat: number;
    lng: number;
    vehicleType?: "Car" | "Motorbike";
    limit?: number;
  }): Promise<
    DjangoPaginatedResponse<
      ParkingLot & { distance?: number; availableSlots?: number }
    >
  > => {
    const queryParams: Record<string, string> = {
      lat: String(params.lat),
      lng: String(params.lng),
    };
    if (params.vehicleType) queryParams.vehicle_type = params.vehicleType;
    if (params.limit) queryParams.limit = String(params.limit);

    const response = await apiClient.get("/parking/lots/nearest/", {
      params: queryParams,
    });
    return response.data;
  },

  /**
   * Get floors for a parking lot
   */
  getFloors: async (
    params: GetFloorsParams,
  ): Promise<DjangoPaginatedResponse<Floor>> => {
    const queryParams: Record<string, string> = buildPaginationParams(params);
    queryParams.lot_id = params.lot_id;

    const response = await apiClient.get<DjangoPaginatedResponse<Floor>>(
      "/parking/floors/",
      { params: queryParams },
    );
    return response.data;
  },

  /**
   * Get zones for a parking lot
   */
  getZones: async (
    params: GetZonesParams,
  ): Promise<DjangoPaginatedResponse<ParkingZone>> => {
    const queryParams: Record<string, string> = buildPaginationParams(params);
    queryParams.lot_id = params.lot_id;
    if (params.floor !== undefined) queryParams.floor = String(params.floor);
    if (params.vehicle_type) queryParams.vehicle_type = params.vehicle_type;

    const response = await apiClient.get<DjangoPaginatedResponse<ParkingZone>>(
      "/parking/zones/",
      { params: queryParams },
    );
    return response.data;
  },

  /**
   * Get single zone details
   */
  getZone: async (zoneId: string): Promise<ParkingZone> => {
    const response = await apiClient.get<ParkingZone>(
      `/parking/zones/${zoneId}/`,
    );
    return response.data;
  },

  /**
   * Get slots for a zone
   */
  getSlots: async (
    params: GetSlotsParams,
  ): Promise<DjangoPaginatedResponse<ParkingSlot>> => {
    const queryParams: Record<string, string> = buildPaginationParams(params);
    if (params.zone_id) queryParams.zone_id = params.zone_id;
    if (params.status) queryParams.status = params.status;

    const response = await apiClient.get<DjangoPaginatedResponse<ParkingSlot>>(
      "/parking/slots/",
      { params: queryParams },
    );
    return response.data;
  },

  /**
   * Get single slot details
   */
  getSlot: async (slotId: string): Promise<ParkingSlot> => {
    const response = await apiClient.get<ParkingSlot>(
      `/parking/slots/${slotId}/`,
    );
    return response.data;
  },

  /**
   * Check slot availability for a time range
   */
  checkAvailability: async (
    params: CheckAvailabilityParams,
  ): Promise<CheckAvailabilityResponse> => {
    const response = await apiClient.post<CheckAvailabilityResponse>(
      "/parking/slots/check-availability/",
      params,
    );
    return response.data;
  },

  /**
   * Get realtime availability summary for a lot
   */
  getLotAvailability: async (
    lotId: string,
  ): Promise<{
    total: number;
    available: number;
    occupied: number;
    reserved: number;
    byVehicleType: {
      car: { available: number; total: number };
      motorbike: { available: number; total: number };
    };
  }> => {
    const response = await apiClient.get(
      `/parking/lots/${lotId}/availability/`,
    );
    return response.data;
  },
  /**
   * Get zone availability
   */
  getZoneAvailability: async (
    zoneId: string,
  ): Promise<{
    total: number;
    available: number;
    occupied: number;
    reserved: number;
  }> => {
    const response = await apiClient.get(
      `/parking/zones/${zoneId}/availability/`,
    );
    return response.data;
  },

  /**
   * Update slot status (called by AI service / admin).
   */
  updateSlotStatus: async (
    slotId: string,
    status: "available" | "occupied" | "reserved" | "maintenance",
  ): Promise<{
    slotId: string;
    oldStatus: string;
    newStatus: string;
    zoneAvailable: number;
    lotAvailable: number;
    message: string;
  }> => {
    const response = await apiClient.patch(
      `/parking/slots/${slotId}/update-status/`,
      { status },
    );
    return response.data;
  },
};
