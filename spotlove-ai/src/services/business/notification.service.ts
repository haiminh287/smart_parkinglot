/**
 * Notification Business Service
 * Business logic layer - manages notifications + realtime
 *
 * Pattern: service.ts = Business Logic + Redux + WebSocket Integration
 *          api.ts = Pure HTTP calls only
 */

import { notificationApi } from "@/services/api/notification.api";
import { websocketService } from "@/services/websocket.service";
import { store } from "@/store";
import {
  addNotification,
  updateNotification,
  clearNotifications,
} from "@/store/slices/notificationSlice";
import type {
  Notification,
  NotificationType,
} from "@/store/slices/notificationSlice";
import type {
  DjangoPaginatedResponse,
  PaginationParams,
} from "@/services/api/axios.client";

// =====================
// Types
// =====================

export interface NotificationFilters extends PaginationParams {
  type?: NotificationType;
  isRead?: boolean;
}

export interface NotificationPreferences {
  pushEnabled: boolean;
  emailEnabled: boolean;
  types: NotificationType[];
}

// =====================
// Notification Business Service
// =====================

export const notificationService = {
  /**
   * Get notifications with filters
   */
  async getAll(
    filters?: NotificationFilters,
  ): Promise<DjangoPaginatedResponse<Notification>> {
    return notificationApi.getNotifications({
      page: filters?.page,
      pageSize: filters?.pageSize,
      type: filters?.type,
      isRead: filters?.isRead,
    });
  },

  /**
   * Get unread count and update Redux
   */
  async getUnreadCount(): Promise<number> {
    const response = await notificationApi.getUnreadCount();
    // Note: Redux state is updated via async thunk
    return response.count;
  },

  /**
   * Mark single notification as read
   */
  async markAsRead(notificationId: string): Promise<void> {
    await notificationApi.markAsRead(notificationId);
    // Redux state updated via async thunk
  },

  /**
   * Mark all notifications as read
   */
  async markAllAsRead(): Promise<void> {
    await notificationApi.markAllAsRead();
    // Redux state updated via async thunk
  },

  /**
   * Delete a notification
   */
  async delete(notificationId: string): Promise<void> {
    await notificationApi.deleteNotification(notificationId);
    // Manually update Redux - remove from list
  },

  /**
   * Clear all notifications
   */
  async clearAll(): Promise<void> {
    await notificationApi.clearAll();
    store.dispatch(clearNotifications());
  },

  /**
   * Get notification preferences
   */
  async getPreferences(): Promise<NotificationPreferences> {
    const prefs = await notificationApi.getPreferences();
    return {
      pushEnabled: prefs.pushEnabled,
      emailEnabled: prefs.emailEnabled,
      types: prefs.types,
    };
  },

  /**
   * Update notification preferences
   */
  async updatePreferences(preferences: NotificationPreferences): Promise<void> {
    await notificationApi.updatePreferences({
      pushEnabled: preferences.pushEnabled,
      emailEnabled: preferences.emailEnabled,
      types: preferences.types,
    });
  },

  /**
   * Handle realtime notification from WebSocket
   * Called by websocketService.processMessage
   */
  handleNewNotification(notification: Notification): void {
    store.dispatch(addNotification(notification));
  },

  /**
   * Request browser push notification permission
   */
  async requestPushPermission(): Promise<boolean> {
    if (!("Notification" in window)) {
      return false;
    }

    const permission = await Notification.requestPermission();
    return permission === "granted";
  },

  /**
   * Show browser notification
   */
  showBrowserNotification(title: string, options?: NotificationOptions): void {
    if (Notification.permission === "granted") {
      new Notification(title, {
        icon: "/favicon.ico",
        ...options,
      });
    }
  },
};
