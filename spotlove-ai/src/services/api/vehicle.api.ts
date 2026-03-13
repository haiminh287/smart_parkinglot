/**
 * Vehicle API Service
 * API calls for vehicle management with Django REST pagination
 */

import apiClient, {
  buildPaginationParams,
  type DjangoPaginatedResponse,
  type PaginationParams,
} from "./axios.client";

// =====================
// Types
// =====================

export interface Vehicle {
  id: string;
  licensePlate: string;
  vehicleType: "Car" | "Motorbike";
  brand?: string;
  model?: string;
  color?: string;
  isDefault: boolean;
  createdAt: string;
}

export interface CreateVehicleRequest {
  licensePlate: string;
  vehicleType: "Car" | "Motorbike";
  brand?: string;
  model?: string;
  color?: string;
  isDefault?: boolean;
}

export interface UpdateVehicleRequest {
  licensePlate?: string;
  brand?: string;
  model?: string;
  color?: string;
  isDefault?: boolean;
}

// =====================
// API Endpoints
// =====================

export const vehicleApi = {
  /**
   * Get list of user's vehicles
   */
  getVehicles: async (
    params?: PaginationParams,
  ): Promise<DjangoPaginatedResponse<Vehicle>> => {
    const queryParams = buildPaginationParams(params || {});
    const response = await apiClient.get<DjangoPaginatedResponse<Vehicle>>(
      "/vehicles/",
      { params: queryParams },
    );
    return response.data;
  },

  /**
   * Get single vehicle details
   */
  getVehicle: async (vehicleId: string): Promise<Vehicle> => {
    const response = await apiClient.get<Vehicle>(`/vehicles/${vehicleId}/`);
    return response.data;
  },

  /**
   * Create new vehicle
   */
  createVehicle: async (data: CreateVehicleRequest): Promise<Vehicle> => {
    const response = await apiClient.post<Vehicle>("/vehicles/", data);
    return response.data;
  },

  /**
   * Update vehicle
   */
  updateVehicle: async (
    vehicleId: string,
    data: UpdateVehicleRequest,
  ): Promise<Vehicle> => {
    const response = await apiClient.patch<Vehicle>(
      `/vehicles/${vehicleId}/`,
      data,
    );
    return response.data;
  },

  /**
   * Delete vehicle
   */
  deleteVehicle: async (vehicleId: string): Promise<void> => {
    await apiClient.delete(`/vehicles/${vehicleId}/`);
  },

  /**
   * Set vehicle as default
   */
  setAsDefault: async (vehicleId: string): Promise<Vehicle> => {
    const response = await apiClient.post<Vehicle>(
      `/vehicles/${vehicleId}/set-default/`,
    );
    return response.data;
  },

  /**
   * Get default vehicle
   */
  getDefaultVehicle: async (): Promise<Vehicle | null> => {
    const response = await apiClient.get("/vehicles/default/");
    return response.data;
  },
};
