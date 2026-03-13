/**
 * Admin Business Service
 * Business logic layer - handles admin operations
 *
 * Pattern: service.ts = Business Logic + Redux Integration
 *          api.ts = Pure HTTP calls only
 */

import { adminApi } from "@/services/api/admin.api";
import type {
  User,
  DashboardStats,
  RevenueReport,
  IncidentReport,
  SystemConfig,
  ParkingLotInput,
  ZoneInput,
  CameraInput,
} from "@/services/api/admin.api";
import type {
  DjangoPaginatedResponse,
  PaginationParams,
} from "@/services/api/axios.client";

// =====================
// Types
// =====================

export interface UserFilters {
  role?: "user" | "admin";
  isActive?: boolean;
  search?: string;
  page?: number;
  pageSize?: number;
}

export interface RevenueReportParams {
  startDate: string;
  endDate: string;
  groupBy: "day" | "week" | "month";
}

export interface OperationResult {
  success: boolean;
  message: string;
}

interface ApiErrorPayload {
  response?: {
    data?: {
      message?: string;
    };
  };
}

const getApiErrorMessage = (error: unknown, fallbackMessage: string): string => {
  const apiError = error as ApiErrorPayload;
  return apiError.response?.data?.message || fallbackMessage;
};

// =====================
// Admin Business Service
// =====================

export const adminService = {
  // =====================
  // Dashboard
  // =====================

  /**
   * Get dashboard stats
   */
  async getDashboardStats(): Promise<DashboardStats> {
    return adminApi.getDashboardStats();
  },

  /**
   * Get revenue report
   */
  async getRevenueReport(
    params: RevenueReportParams,
  ): Promise<RevenueReport[]> {
    return adminApi.getRevenueReport({
      startDate: params.startDate,
      endDate: params.endDate,
      groupBy: params.groupBy,
    });
  },

  /**
   * Get recent activities
   */
  async getRecentActivities(limit?: number) {
    return adminApi.getRecentActivities(limit);
  },

  // =====================
  // User Management
  // =====================

  /**
   * Get users list with filters
   */
  async getUsers(
    filters?: UserFilters,
  ): Promise<DjangoPaginatedResponse<User>> {
    return adminApi.getUsers({
      page: filters?.page,
      pageSize: filters?.pageSize,
      role: filters?.role,
      isActive: filters?.isActive,
      search: filters?.search,
    });
  },

  /**
   * Get single user
   */
  async getUser(userId: string): Promise<User> {
    return adminApi.getUser(userId);
  },

  /**
   * Update user
   */
  async updateUser(
    userId: string,
    data: Partial<User>,
  ): Promise<OperationResult> {
    try {
      await adminApi.updateUser(userId, data);
      return { success: true, message: "Cập nhật user thành công" };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Lỗi cập nhật user"),
      };
    }
  },

  /**
   * Deactivate user
   */
  async deactivateUser(userId: string): Promise<OperationResult> {
    try {
      await adminApi.deactivateUser(userId);
      return { success: true, message: "Đã khóa tài khoản user" };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Lỗi khóa user"),
      };
    }
  },

  /**
   * Activate user
   */
  async activateUser(userId: string): Promise<OperationResult> {
    try {
      await adminApi.activateUser(userId);
      return { success: true, message: "Đã mở khóa tài khoản user" };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Lỗi mở khóa user"),
      };
    }
  },

  /**
   * Reset user's no-show count
   */
  async resetNoShowCount(userId: string): Promise<OperationResult> {
    try {
      await adminApi.resetNoShowCount(userId);
      return { success: true, message: "Đã reset số lần vi phạm" };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Lỗi reset vi phạm"),
      };
    }
  },

  // =====================
  // Parking Management
  // =====================

  /**
   * Create parking lot
   */
  async createLot(data: {
    name: string;
    address: string;
    lat: number;
    lng: number;
  }) {
    return adminApi.createLot(data);
  },

  /**
   * Update parking lot
   */
  async updateLot(lotId: string, data: Partial<ParkingLotInput>) {
    return adminApi.updateLot(lotId, data);
  },

  /**
   * Create zone
   */
  async createZone(data: {
    lotId: string;
    name: string;
    floor: number;
    vehicleType: "Car" | "Motorbike";
    totalSlots: number;
  }) {
    return adminApi.createZone({
      lotId: data.lotId,
      name: data.name,
      floor: data.floor,
      vehicleType: data.vehicleType,
      totalSlots: data.totalSlots,
    });
  },

  /**
   * Update zone
   */
  async updateZone(zoneId: string, data: Partial<ZoneInput>) {
    return adminApi.updateZone(zoneId, data);
  },

  /**
   * Update slot status
   */
  async updateSlotStatus(
    slotId: string,
    status: string,
  ): Promise<OperationResult> {
    try {
      await adminApi.updateSlotStatus(slotId, status);
      return { success: true, message: "Cập nhật trạng thái slot thành công" };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Lỗi cập nhật slot"),
      };
    }
  },

  // =====================
  // Incident Management
  // =====================

  /**
   * Get incidents
   */
  async getIncidents(
    params?: PaginationParams & { status?: string },
  ): Promise<DjangoPaginatedResponse<IncidentReport>> {
    return adminApi.getIncidents(params);
  },

  /**
   * Update incident status
   */
  async updateIncidentStatus(
    incidentId: string,
    status: "in_progress" | "resolved",
    resolution?: string,
  ): Promise<OperationResult> {
    try {
      await adminApi.updateIncidentStatus(incidentId, status, resolution);
      return { success: true, message: "Cập nhật sự cố thành công" };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Lỗi cập nhật sự cố"),
      };
    }
  },

  // =====================
  // System Configuration
  // =====================

  /**
   * Get system config
   */
  async getConfig(): Promise<SystemConfig> {
    return adminApi.getConfig();
  },

  /**
   * Update system config
   */
  async updateConfig(data: Partial<SystemConfig>): Promise<OperationResult> {
    try {
      await adminApi.updateConfig(data);
      return { success: true, message: "Cập nhật cấu hình thành công" };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Lỗi cập nhật cấu hình"),
      };
    }
  },

  // =====================
  // Camera Management
  // =====================

  /**
   * Get cameras
   */
  async getCameras(params?: PaginationParams) {
    return adminApi.getCameras(params);
  },

  /**
   * Update camera
   */
  async updateCamera(cameraId: string, data: Partial<CameraInput>) {
    return adminApi.updateCamera(cameraId, data);
  },
};
