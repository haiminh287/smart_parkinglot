/**
 * Notification Slice
 * Manages realtime notifications
 */

import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { notificationService } from "@/services/business";

export type NotificationType =
  | "booking"
  | "payment"
  | "incident"
  | "system"
  | "marketing";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  data?: Record<string, unknown>;
  isRead: boolean;
  createdAt: string;
}

interface ApiErrorPayload {
  response?: {
    data?: {
      message?: string;
    };
  };
}

const getErrorMessage = (error: unknown, fallbackMessage: string): string => {
  const apiError = error as ApiErrorPayload;
  return apiError.response?.data?.message || fallbackMessage;
};

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
  // Pagination
  pagination: {
    count: number;
    next: string | null;
    previous: string | null;
  };
}

const initialState: NotificationState = {
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null,
  pagination: {
    count: 0,
    next: null,
    previous: null,
  },
};

// Async thunks
export const fetchNotifications = createAsyncThunk(
  "notification/fetchNotifications",
  async (params: { page?: number } | undefined, { rejectWithValue }) => {
    try {
      const response = await notificationService.getAll(params);
      return {
        results: response.results,
        count: response.count,
        next: response.next,
        previous: response.previous,
      };
    } catch (error: unknown) {
      return rejectWithValue(getErrorMessage(error, "Không thể tải thông báo"));
    }
  },
);

export const markAsRead = createAsyncThunk(
  "notification/markAsRead",
  async (notificationId: string, { rejectWithValue }) => {
    try {
      await notificationService.markAsRead(notificationId);
      return notificationId;
    } catch (error: unknown) {
      return rejectWithValue(
        getErrorMessage(error, "Không thể đánh dấu đã đọc"),
      );
    }
  },
);

export const markAllAsRead = createAsyncThunk(
  "notification/markAllAsRead",
  async (_, { rejectWithValue }) => {
    try {
      await notificationService.markAllAsRead();
    } catch (error: unknown) {
      return rejectWithValue(
        getErrorMessage(error, "Không thể đánh dấu tất cả đã đọc"),
      );
    }
  },
);

const notificationSlice = createSlice({
  name: "notification",
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    // Realtime: Add new notification from WebSocket
    addNotification: (state, action: PayloadAction<Notification>) => {
      state.notifications.unshift(action.payload);
      if (!action.payload.isRead) {
        state.unreadCount += 1;
      }
      state.pagination.count += 1;
    },
    // Realtime: Update notification
    updateNotification: (state, action: PayloadAction<Notification>) => {
      const index = state.notifications.findIndex(
        (n) => n.id === action.payload.id,
      );
      if (index !== -1) {
        const wasUnread = !state.notifications[index].isRead;
        const isNowRead = action.payload.isRead;
        state.notifications[index] = action.payload;
        if (wasUnread && isNowRead) {
          state.unreadCount = Math.max(0, state.unreadCount - 1);
        }
      }
    },
    // Clear all notifications
    clearNotifications: (state) => {
      state.notifications = [];
      state.unreadCount = 0;
      state.pagination = { count: 0, next: null, previous: null };
    },
  },
  extraReducers: (builder) => {
    // Fetch notifications
    builder
      .addCase(fetchNotifications.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchNotifications.fulfilled, (state, action) => {
        state.isLoading = false;
        state.notifications = action.payload.results;
        state.unreadCount = action.payload.results.filter(
          (n) => !n.isRead,
        ).length;
        state.pagination = {
          count: action.payload.count,
          next: action.payload.next,
          previous: action.payload.previous,
        };
      })
      .addCase(fetchNotifications.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Mark as read
    builder.addCase(markAsRead.fulfilled, (state, action) => {
      const notification = state.notifications.find(
        (n) => n.id === action.payload,
      );
      if (notification && !notification.isRead) {
        notification.isRead = true;
        state.unreadCount = Math.max(0, state.unreadCount - 1);
      }
    });

    // Mark all as read
    builder.addCase(markAllAsRead.fulfilled, (state) => {
      state.notifications.forEach((n) => {
        n.isRead = true;
      });
      state.unreadCount = 0;
    });
  },
});

export const {
  clearError,
  addNotification,
  updateNotification,
  clearNotifications,
} = notificationSlice.actions;

export default notificationSlice.reducer;
