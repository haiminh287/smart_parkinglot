/**
 * Incident API Service
 * API calls for incident/panic button with Django REST pagination
 */

import apiClient, {
  buildPaginationParams,
  type DjangoPaginatedResponse,
  type PaginationParams,
} from "./axios.client";

// =====================
// Types
// =====================

export type IncidentType =
  | "vehicle_damage"
  | "theft"
  | "accident"
  | "emergency"
  | "suspicious_activity"
  | "other";

export type IncidentStatus =
  | "pending"
  | "in_progress"
  | "resolved"
  | "cancelled";

export interface Incident {
  id: string;
  type: IncidentType;
  description?: string;
  status: IncidentStatus;
  userId: string;
  bookingId?: string;
  parkingLotId?: string;
  zoneId?: string;
  zoneName?: string;
  slotId?: string;
  slotCode?: string;
  latitude?: number;
  longitude?: number;
  securityNotified: boolean;
  securityNotifiedAt?: string;
  resolvedAt?: string;
  resolutionNotes?: string;
  resolvedBy?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ReportIncidentRequest {
  type: IncidentType;
  description?: string;
  bookingId?: string;
  location?: {
    zoneId?: string;
    slotId?: string;
  };
}

export interface ReportIncidentResponse {
  incident: Incident;
  message: string;
}

// =====================
// API Endpoints
// =====================

export const incidentApi = {
  /**
   * Report new incident (Panic Button)
   */
  reportIncident: async (
    data: ReportIncidentRequest,
  ): Promise<ReportIncidentResponse> => {
    const response = await apiClient.post<ReportIncidentResponse>(
      "/incidents/",
      data,
    );
    return response.data;
  },

  /**
   * Get all incidents (admin view)
   */
  getIncidents: async (
    params?: PaginationParams,
  ): Promise<DjangoPaginatedResponse<Incident>> => {
    const queryParams = buildPaginationParams(params || {});
    const response = await apiClient.get<DjangoPaginatedResponse<Incident>>(
      "/incidents/",
      { params: queryParams },
    );
    return response.data;
  },

  /**
   * Get user's incidents history
   */
  getMyIncidents: async (
    params?: PaginationParams,
  ): Promise<DjangoPaginatedResponse<Incident>> => {
    const queryParams = buildPaginationParams(params || {});
    const response = await apiClient.get<DjangoPaginatedResponse<Incident>>(
      "/incidents/my/",
      { params: queryParams },
    );
    return response.data;
  },

  /**
   * Get incident details
   */
  getIncident: async (incidentId: string): Promise<Incident> => {
    const response = await apiClient.get<Incident>(`/incidents/${incidentId}/`);
    return response.data;
  },

  /**
   * Cancel incident report
   */
  cancelIncident: async (
    incidentId: string,
    reason?: string,
  ): Promise<void> => {
    await apiClient.post(`/incidents/${incidentId}/cancel/`, { reason });
  },

  /**
   * Get nearby camera for incident location
   */
  getNearbyCamera: async (params: {
    zoneId?: string;
    slotId?: string;
  }): Promise<{
    cameraId: string;
    streamUrl: string;
  }> => {
    const response = await apiClient.get("/incidents/nearby-camera/", {
      params,
    });
    return response.data;
  },

  /**
   * Request security assistance
   */
  requestSecurity: async (
    incidentId: string,
  ): Promise<{
    securityNotified: boolean;
    estimatedArrival: number;
    message: string;
  }> => {
    const response = await apiClient.post(
      `/incidents/${incidentId}/request-security/`,
    );
    return response.data;
  },

  /**
   * Resolve incident (admin action)
   */
  resolveIncident: async (
    incidentId: string,
    data: { resolution: string },
  ): Promise<void> => {
    await apiClient.post(`/incidents/${incidentId}/resolve/`, data);
  },
};
