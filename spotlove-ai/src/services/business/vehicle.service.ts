/**
 * Vehicle Business Service
 * Business logic layer - manages user's vehicles
 *
 * Pattern: service.ts = Business Logic + Redux Integration
 *          api.ts = Pure HTTP calls only
 */

import { vehicleApi } from "@/services/api/vehicle.api";
import type {
  Vehicle,
  CreateVehicleRequest,
  UpdateVehicleRequest,
} from "@/services/api/vehicle.api";
import type {
  DjangoPaginatedResponse,
  PaginationParams,
} from "@/services/api/axios.client";

// =====================
// Re-export Types for consumers
// =====================

export type CreateVehicleData = CreateVehicleRequest;

// =====================
// Types
// =====================

export interface VehicleResult {
  success: boolean;
  vehicle?: Vehicle;
  message: string;
}

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
// Vehicle Business Service
// =====================

export const vehicleService = {
  /**
   * Get all user's vehicles
   */
  async getAll(
    params?: PaginationParams,
  ): Promise<DjangoPaginatedResponse<Vehicle>> {
    return vehicleApi.getVehicles(params);
  },

  /**
   * Get single vehicle
   */
  async getById(vehicleId: string): Promise<Vehicle> {
    return vehicleApi.getVehicle(vehicleId);
  },

  /**
   * Create new vehicle
   * - Validates license plate format
   * - Creates vehicle
   */
  async create(data: CreateVehicleRequest): Promise<VehicleResult> {
    try {
      // Validate license plate format (Vietnamese format)
      if (!this.validateLicensePlate(data.licensePlate)) {
        return { success: false, message: "Biển số xe không hợp lệ" };
      }

      const vehicle = await vehicleApi.createVehicle(data);

      return {
        success: true,
        vehicle,
        message: "Thêm xe thành công",
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Không thể thêm xe"),
      };
    }
  },

  /**
   * Update vehicle
   */
  async update(
    vehicleId: string,
    data: UpdateVehicleRequest,
  ): Promise<VehicleResult> {
    try {
      if (data.licensePlate && !this.validateLicensePlate(data.licensePlate)) {
        return { success: false, message: "Biển số xe không hợp lệ" };
      }

      const vehicle = await vehicleApi.updateVehicle(vehicleId, data);

      return {
        success: true,
        vehicle,
        message: "Cập nhật xe thành công",
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Không thể cập nhật xe"),
      };
    }
  },

  /**
   * Delete vehicle
   */
  async delete(vehicleId: string): Promise<VehicleResult> {
    try {
      await vehicleApi.deleteVehicle(vehicleId);

      return {
        success: true,
        message: "Xóa xe thành công",
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Không thể xóa xe"),
      };
    }
  },

  /**
   * Set vehicle as default
   */
  async setDefault(vehicleId: string): Promise<VehicleResult> {
    try {
      const vehicle = await vehicleApi.setAsDefault(vehicleId);

      return {
        success: true,
        vehicle,
        message: "Đã đặt làm xe mặc định",
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Không thể đặt làm mặc định"),
      };
    }
  },

  /**
   * Get default vehicle
   */
  async getDefault(): Promise<Vehicle | null> {
    return vehicleApi.getDefaultVehicle();
  },

  /**
   * Validate Vietnamese license plate format
   * Formats: 51A-123.45, 59X1-999.99, etc.
   */
  validateLicensePlate(plate: string): boolean {
    // Vietnamese license plate patterns
    const patterns = [
      /^\d{2}[A-Z]\d?-\d{3,4}\.\d{2}$/, // Car: 51A-123.45 or 51A1-1234.56
      /^\d{2}[A-Z]\d-\d{3}\.\d{2}$/, // Motorbike: 59X1-999.99
      /^\d{2}[A-Z]-\d{3}\.\d{2}$/, // Old format: 51A-123.45
    ];

    const normalizedPlate = plate.toUpperCase().trim();
    return patterns.some((pattern) => pattern.test(normalizedPlate));
  },

  /**
   * Format license plate for display
   */
  formatPlate(plate: string): string {
    return plate.toUpperCase().trim();
  },
};
