/**
 * Incident Business Service
 * Business logic layer - handles panic button and incidents
 *
 * Pattern: service.ts = Business Logic + Redux + WebSocket Integration
 *          api.ts = Pure HTTP calls only
 */

import { incidentApi } from "@/services/api/incident.api";
import { websocketService } from "@/services/websocket.service";
import type {
  Incident,
  IncidentType,
  ReportIncidentRequest,
} from "@/services/api/incident.api";
import type {
  DjangoPaginatedResponse,
  PaginationParams,
} from "@/services/api/axios.client";

// =====================
// Types
// =====================

export interface ReportIncidentData {
  type: IncidentType;
  description?: string;
  bookingId?: string;
  zoneId?: string;
  slotId?: string;
}

export interface IncidentResult {
  success: boolean;
  incident?: Incident;
  cameraStream?: string;
  estimatedResponseTime?: number;
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
// Incident Business Service
// =====================

export const incidentService = {
  /**
   * Report new incident (Panic Button)
   * - Reports to backend
   * - Subscribes to incident updates
   * - Triggers notifications
   */
  async report(data: ReportIncidentData): Promise<IncidentResult> {
    try {
      const request: ReportIncidentRequest = {
        type: data.type,
        description: data.description,
        bookingId: data.bookingId,
        location: {
          zoneId: data.zoneId,
          slotId: data.slotId,
        },
      };

      const response = await incidentApi.reportIncident(request);

      // Subscribe to incident updates
      websocketService.subscribe(`incident.${response.incident.id}`);

      return {
        success: true,
        incident: response.incident,
        message: response.message,
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Không thể báo cáo sự cố"),
      };
    }
  },

  /**
   * Get my reported incidents
   */
  async getMyIncidents(
    params?: PaginationParams,
  ): Promise<DjangoPaginatedResponse<Incident>> {
    return incidentApi.getMyIncidents(params);
  },

  /**
   * Get incident details
   */
  async getById(incidentId: string): Promise<Incident> {
    return incidentApi.getIncident(incidentId);
  },

  /**
   * Cancel incident report
   */
  async cancel(incidentId: string, reason?: string): Promise<IncidentResult> {
    try {
      await incidentApi.cancelIncident(incidentId, reason);

      // Unsubscribe from updates
      websocketService.unsubscribe(`incident.${incidentId}`);

      return {
        success: true,
        message: "Đã hủy báo cáo sự cố",
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Không thể hủy báo cáo"),
      };
    }
  },

  /**
   * Get nearby camera for incident location
   */
  async getNearbyCamera(
    zoneId?: string,
    slotId?: string,
  ): Promise<{ cameraId: string; streamUrl: string } | null> {
    try {
      const response = await incidentApi.getNearbyCamera({
        zoneId: zoneId,
        slotId: slotId,
      });
      return {
        cameraId: response.cameraId,
        streamUrl: response.streamUrl,
      };
    } catch (error) {
      return null;
    }
  },

  /**
   * Request security assistance for an incident
   */
  async requestSecurity(incidentId: string): Promise<IncidentResult> {
    try {
      const response = await incidentApi.requestSecurity(incidentId);

      return {
        success: true,
        estimatedResponseTime: response.estimatedArrival,
        message: response.message,
      };
    } catch (error: unknown) {
      return {
        success: false,
        message: getApiErrorMessage(error, "Không thể gọi bảo vệ"),
      };
    }
  },

  /**
   * Get incident type label
   */
  getTypeLabel(type: IncidentType): string {
    const labels: Record<IncidentType, string> = {
      vehicle_damage: "Xe bị hư hại",
      theft: "Trộm cắp",
      accident: "Tai nạn",
      emergency: "Khẩn cấp",
      suspicious_activity: "Hoạt động đáng ngờ",
      other: "Khác",
    };
    return labels[type] || type;
  },
};
