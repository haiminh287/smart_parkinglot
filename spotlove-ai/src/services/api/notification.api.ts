/**
 * Notification API Service
 * API calls for notifications with Django REST pagination
 */

import apiClient, {
  buildPaginationParams,
  type DjangoPaginatedResponse,
  type PaginationParams,
} from "./axios.client";
import type {
  Notification,
  NotificationType,
} from "@/store/slices/notificationSlice";

// =====================
// Types
// =====================

export interface GetNotificationsParams extends PaginationParams {
  type?: NotificationType;
  isRead?: boolean;
}

interface NotificationWithLegacyType extends Notification {
  notificationType?: NotificationType;
}

// =====================
// API Endpoints
// =====================

export const notificationApi = {
  /**
   * Get list of notifications with pagination
   */
  getNotifications: async (
    params?: GetNotificationsParams,
  ): Promise<DjangoPaginatedResponse<Notification>> => {
    const queryParams: Record<string, string> = {};

    if (params) {
      Object.assign(queryParams, buildPaginationParams(params));
      if (params.type) queryParams.type = params.type;
      if (params.isRead !== undefined)
        queryParams.is_read = String(params.isRead);
    }

    const response = await apiClient.get<DjangoPaginatedResponse<Notification>>(
      "/notifications/",
      { params: queryParams },
    );
    // Backend sends `notificationType` (camelCase of notification_type)
    // but frontend Notification interface expects `type`.  Map here.
    const data = response.data;
    if (data.results) {
      data.results = data.results.map((n: NotificationWithLegacyType) => ({
        ...n,
        type: n.type ?? n.notificationType ?? "system",
      }));
    }
    return data;
  },

  /**
   * Get unread notification count
   * Backend returns { unread_count } (FastAPI, no camelCase renderer)
   */
  getUnreadCount: async (): Promise<{ count: number }> => {
    const response = await apiClient.get("/notifications/unread-count/");
    // Backend returns { unread_count: N } or { unreadCount: N } — normalize
    const data = response.data;
    return { count: data.count ?? data.unread_count ?? data.unreadCount ?? 0 };
  },

  /**
   * Mark notification(s) as read — backend uses batch API
   */
  markAsRead: async (notificationId: string): Promise<void> => {
    await apiClient.post("/notifications/mark-read/", {
      notification_ids: [notificationId],
    });
  },

  /**
   * Mark all notifications as read
   */
  markAllAsRead: async (): Promise<void> => {
    await apiClient.post("/notifications/mark-all-read/");
  },

  /**
   * Delete notification — NOT implemented in backend, silent no-op
   */
  deleteNotification: async (_notificationId: string): Promise<void> => {
    // Backend does not implement DELETE for notifications
    console.warn("deleteNotification: not implemented in backend");
  },

  /**
   * Clear all notifications — NOT implemented in backend, silent no-op
   */
  clearAll: async (): Promise<void> => {
    // Backend does not implement clear-all for notifications
    console.warn("clearAll: not implemented in backend");
  },

  /**
   * Update notification preferences
   */
  updatePreferences: async (preferences: {
    pushEnabled: boolean;
    emailEnabled: boolean;
    types: NotificationType[];
  }): Promise<void> => {
    await apiClient.put("/notifications/preferences/", preferences);
  },

  /**
   * Get notification preferences
   */
  getPreferences: async (): Promise<{
    pushEnabled: boolean;
    emailEnabled: boolean;
    types: NotificationType[];
  }> => {
    const response = await apiClient.get("/notifications/preferences/");
    return response.data;
  },
};
