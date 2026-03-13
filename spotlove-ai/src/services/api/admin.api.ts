/**
 * Admin API Service
 * API calls for admin dashboard and management with Django REST pagination
 *
 * IMPORTANT: Backend uses djangorestframework-camel-case:
 *   - CamelCaseJSONParser:  converts input camelCase keys → snake_case
 *   - CamelCaseJSONRenderer: converts output snake_case keys → camelCase
 * So we always send camelCase from the frontend.
 *
 * Routing:
 *   /auth/admin/*  → auth-service (dashboard stats, user CRUD)
 *   /parking/*     → parking-service (lots, floors, zones, slots, cameras)
 *   /incidents/*   → booking-service (incident management)
 */

import apiClient, {
  buildPaginationParams,
  type DjangoPaginatedResponse,
  type PaginationParams,
} from "./axios.client";

// ==================== Types ====================

export interface User {
  id: string;
  email: string;
  username: string;
  phone?: string;
  avatar?: string;
  role: "user" | "admin";
  isActive: boolean;
  isStaff?: boolean;
  address?: string;
  noShowCount: number;
  totalBookings: number;
  createdAt: string;
  dateJoined?: string;
  lastLogin?: string;
  status?: "active" | "banned";
  totalSpent?: number;
}

export interface CreateUserData {
  email: string;
  username: string;
  password: string;
  role?: "user" | "admin";
  phone?: string;
  isActive?: boolean;
  isStaff?: boolean;
}

export interface GetUsersParams extends PaginationParams {
  role?: "user" | "admin";
  isActive?: boolean;
}

export interface DashboardStats {
  totalUsers: number;
  totalBookings: number;
  totalRevenue: number;
  activeParkings: number;
  occupancyRate: number;
  usersChange: number;
  bookingsChange: number;
  revenueChange: number;
}

export interface RevenueReport {
  period: string;
  revenue: number;
  bookings: number;
}

export interface IncidentReport {
  id: string;
  type: string;
  description: string;
  status: "pending" | "in_progress" | "resolved";
  reportedBy: string;
  reportedAt: string;
  resolvedAt?: string;
  zoneId?: string;
  slotId?: string;
}

export interface SystemConfig {
  pricePerHourCar: number;
  pricePerHourMotorbike: number;
  maxNoShowCount: number;
  holdTimeMinutes: number;
  autoCancelMinutes: number;
  onlinePaymentRequiredAfterNoShows: number;
}

export interface SystemConfigUpdatePayload {
  pricing?: {
    car_per_hour?: number;
    motorbike_per_hour?: number;
    currency?: string;
  };
  booking?: {
    hold_time_minutes?: number;
    max_no_show_count?: number;
    auto_cancel_minutes?: number;
  };
}

export interface ParkingLotInput {
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  totalSlots?: number;
  pricePerHour?: number;
}

export interface FloorInput {
  parkingLot: string;
  level: number;
  name: string;
}

export interface ZoneInput {
  floor: string;
  name: string;
  vehicleType: "Car" | "Motorbike";
  capacity: number;
}

export interface SlotInput {
  zone: string;
  code: string;
  status?: string;
  camera?: string | null;
}

export interface CameraInput {
  name: string;
  ipAddress: string;
  port: number;
  zone?: string | null;
  streamUrl?: string;
  isActive?: boolean;
}

// ==================== API ====================

export const adminApi = {
  // ========== Dashboard (auth-service) ==========

  getDashboardStats: async (): Promise<DashboardStats> => {
    const response = await apiClient.get("/auth/admin/dashboard/stats/");
    return response.data;
  },

  getRevenueReport: async (params: {
    startDate: string;
    endDate: string;
    groupBy: "day" | "week" | "month";
  }): Promise<RevenueReport[]> => {
    try {
      const response = await apiClient.get("/auth/admin/reports/revenue/", {
        params,
      });
      return response.data;
    } catch {
      // Endpoint not implemented in backend yet
      return [];
    }
  },

  getRecentActivities: async (
    limit?: number,
  ): Promise<
    { type: string; message: string; timestamp: string; user?: string }[]
  > => {
    try {
      const response = await apiClient.get("/auth/admin/activities/", {
        params: { limit: limit || 10 },
      });
      return response.data;
    } catch {
      // Endpoint not implemented in backend yet
      return [];
    }
  },

  // ========== User Management (auth-service) ==========

  getUsers: async (
    params?: GetUsersParams,
  ): Promise<DjangoPaginatedResponse<User>> => {
    const queryParams: Record<string, string> = {};
    if (params) {
      Object.assign(queryParams, buildPaginationParams(params));
      if (params.role) queryParams.role = params.role;
      if (params.isActive !== undefined)
        queryParams.is_active = String(params.isActive);
    }
    const response = await apiClient.get<DjangoPaginatedResponse<User>>(
      "/auth/admin/users/",
      { params: queryParams },
    );
    return response.data;
  },

  getUser: async (userId: string): Promise<User> => {
    const response = await apiClient.get<User>(`/auth/admin/users/${userId}/`);
    return response.data;
  },

  updateUser: async (userId: string, data: Partial<User>): Promise<User> => {
    const response = await apiClient.patch<User>(
      `/auth/admin/users/${userId}/`,
      data,
    );
    return response.data;
  },

  deactivateUser: async (userId: string): Promise<void> => {
    await apiClient.post(`/auth/admin/users/${userId}/deactivate/`);
  },

  activateUser: async (userId: string): Promise<void> => {
    await apiClient.post(`/auth/admin/users/${userId}/activate/`);
  },

  resetNoShowCount: async (userId: string): Promise<void> => {
    await apiClient.post(`/auth/admin/users/${userId}/reset-no-show/`);
  },

  createUser: async (data: CreateUserData): Promise<User> => {
    const response = await apiClient.post<User>("/auth/admin/users/", data);
    return response.data;
  },

  // ========== Parking Lot Management ==========

  createLot: async (data: ParkingLotInput): Promise<unknown> => {
    const response = await apiClient.post("/parking/lots/", data);
    return response.data;
  },

  updateLot: async (
    lotId: string,
    data: Partial<ParkingLotInput>,
  ): Promise<unknown> => {
    const response = await apiClient.patch(`/parking/lots/${lotId}/`, data);
    return response.data;
  },

  deleteLot: async (lotId: string): Promise<void> => {
    await apiClient.delete(`/parking/lots/${lotId}/`);
  },

  // ========== Floor Management ==========

  createFloor: async (data: FloorInput): Promise<unknown> => {
    const response = await apiClient.post("/parking/floors/", data);
    return response.data;
  },

  updateFloor: async (
    floorId: string,
    data: Partial<FloorInput>,
  ): Promise<unknown> => {
    const response = await apiClient.patch(`/parking/floors/${floorId}/`, data);
    return response.data;
  },

  deleteFloor: async (floorId: string): Promise<void> => {
    await apiClient.delete(`/parking/floors/${floorId}/`);
  },

  // ========== Zone Management ==========

  createZone: async (data: ZoneInput): Promise<unknown> => {
    // Send camelCase — CamelCaseJSONParser converts to snake_case for serializer
    const response = await apiClient.post("/parking/zones/", {
      floor: data.floor,
      name: data.name,
      vehicleType: data.vehicleType,
      capacity: data.capacity,
      availableSlots: data.capacity,
    });
    return response.data;
  },

  updateZone: async (
    zoneId: string,
    data: Partial<ZoneInput>,
  ): Promise<unknown> => {
    const response = await apiClient.patch(`/parking/zones/${zoneId}/`, data);
    return response.data;
  },

  deleteZone: async (zoneId: string): Promise<void> => {
    await apiClient.delete(`/parking/zones/${zoneId}/`);
  },

  // ========== Slot Management ==========

  createSlot: async (data: SlotInput): Promise<unknown> => {
    const response = await apiClient.post("/parking/slots/", {
      zone: data.zone,
      code: data.code,
      status: data.status || "available",
      camera: data.camera || null,
    });
    return response.data;
  },

  updateSlot: async (
    slotId: string,
    data: Partial<SlotInput>,
  ): Promise<unknown> => {
    const response = await apiClient.patch(`/parking/slots/${slotId}/`, data);
    return response.data;
  },

  updateSlotStatus: async (slotId: string, status: string): Promise<void> => {
    await apiClient.patch(`/parking/slots/${slotId}/update-status/`, {
      status,
    });
  },

  deleteSlot: async (slotId: string): Promise<void> => {
    await apiClient.delete(`/parking/slots/${slotId}/`);
  },

  // ========== Incident Management (booking-service) ==========

  getIncidents: async (
    params?: PaginationParams & { status?: string },
  ): Promise<DjangoPaginatedResponse<IncidentReport>> => {
    const queryParams: Record<string, string> = {};
    if (params) {
      Object.assign(queryParams, buildPaginationParams(params));
      if (params.status) queryParams.status = params.status;
    }
    const response = await apiClient.get("/incidents/", {
      params: queryParams,
    });
    return response.data;
  },

  updateIncidentStatus: async (
    incidentId: string,
    status: "in_progress" | "resolved",
    resolution?: string,
  ): Promise<void> => {
    await apiClient.patch(`/incidents/${incidentId}/`, {
      status,
      resolution,
    });
  },

  // ========== System Configuration ==========

  getConfig: async (): Promise<SystemConfig> => {
    try {
      const response = await apiClient.get("/auth/admin/config/");
      return response.data;
    } catch {
      // Fallback defaults if endpoint not available
      return {
        pricePerHourCar: 10000,
        pricePerHourMotorbike: 5000,
        maxNoShowCount: 3,
        holdTimeMinutes: 15,
        autoCancelMinutes: 30,
        onlinePaymentRequiredAfterNoShows: 2,
      };
    }
  },

  updateConfig: async (
    data: Partial<SystemConfig> | SystemConfigUpdatePayload,
  ): Promise<SystemConfig> => {
    const response = await apiClient.patch("/auth/admin/config/", data);
    return response.data;
  },

  // ========== Camera Management ==========

  getCameras: async (
    params?: PaginationParams,
  ): Promise<
    DjangoPaginatedResponse<{
      id: string;
      name: string;
      zone: string;
      ipAddress: string;
      port: number;
      streamUrl: string;
      isActive: boolean;
    }>
  > => {
    const response = await apiClient.get("/parking/cameras/", {
      params: buildPaginationParams(params || {}),
    });
    return response.data;
  },

  createCamera: async (data: CameraInput): Promise<unknown> => {
    const response = await apiClient.post("/parking/cameras/", {
      name: data.name,
      ipAddress: data.ipAddress,
      port: data.port,
      zone: data.zone || null,
      streamUrl:
        data.streamUrl || `rtsp://${data.ipAddress}:${data.port}/stream`,
      isActive: data.isActive !== false,
    });
    return response.data;
  },

  updateCamera: async (
    cameraId: string,
    data: Partial<CameraInput>,
  ): Promise<unknown> => {
    const response = await apiClient.patch(
      `/parking/cameras/${cameraId}/`,
      data,
    );
    return response.data;
  },

  deleteCamera: async (cameraId: string): Promise<void> => {
    await apiClient.delete(`/parking/cameras/${cameraId}/`);
  },

  // ========== Reports ==========

  getDailyStats: async (): Promise<
    { day: string; cars: number; bikes: number; revenue: number }[]
  > => {
    try {
      const response = await apiClient.get("/auth/admin/reports/daily/");
      return response.data;
    } catch {
      // Endpoint not implemented in backend yet
      return [];
    }
  },
};
