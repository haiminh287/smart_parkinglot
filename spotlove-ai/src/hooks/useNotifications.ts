/**
 * useNotifications Hook
 * Provides notification-related functionality using Redux store
 */

import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  fetchNotifications,
  markAsRead,
  markAllAsRead,
  clearNotifications,
  clearError,
} from '@/store/slices/notificationSlice';
import type { NotificationType } from '@/store/slices/notificationSlice';

export function useNotifications() {
  const dispatch = useAppDispatch();
  
  const {
    notifications,
    unreadCount,
    isLoading,
    error,
    pagination,
  } = useAppSelector((state) => state.notification);

  // Fetch notifications
  const loadNotifications = useCallback(
    (params?: { page?: number }) => {
      return dispatch(fetchNotifications(params));
    },
    [dispatch]
  );

  // Mark single notification as read
  const read = useCallback(
    (notificationId: string) => {
      return dispatch(markAsRead(notificationId));
    },
    [dispatch]
  );

  // Mark all notifications as read
  const readAll = useCallback(() => {
    return dispatch(markAllAsRead());
  }, [dispatch]);

  // Clear all notifications
  const clearAll = useCallback(() => {
    dispatch(clearNotifications());
  }, [dispatch]);

  // Clear error
  const clearNotificationError = useCallback(() => {
    dispatch(clearError());
  }, [dispatch]);

  // Filter notifications by type
  const getNotificationsByType = useCallback(
    (type: NotificationType) => {
      return notifications.filter((n) => n.type === type);
    },
    [notifications]
  );

  // Get unread notifications
  const unreadNotifications = notifications.filter((n) => !n.isRead);

  // Get recent notifications (last 5)
  const recentNotifications = notifications.slice(0, 5);

  // Check if there are new notifications
  const hasNewNotifications = unreadCount > 0;

  return {
    // State
    notifications,
    unreadCount,
    isLoading,
    error,
    pagination,
    
    // Derived state
    unreadNotifications,
    recentNotifications,
    hasNewNotifications,
    
    // Actions
    loadNotifications,
    read,
    readAll,
    clearAll,
    clearError: clearNotificationError,
    
    // Helpers
    getNotificationsByType,
  };
}
