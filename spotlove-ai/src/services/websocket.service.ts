/**
 * WebSocket Service
 * Handles realtime connections with Django Channels format: { type: string, data: object }
 */

import { store } from "@/store";
import {
  setStatus,
  setError,
  incrementReconnectAttempts,
  setLastMessageAt,
} from "@/store/slices/websocketSlice";
import {
  updateSlotStatus,
  updateZoneAvailability,
  updateLotAvailability,
  batchUpdateSlots,
} from "@/store/slices/parkingSlice";
import {
  updateBookingStatus,
  updateCurrentParkingCost,
  addNewBooking,
} from "@/store/slices/bookingSlice";
import { addNotification } from "@/store/slices/notificationSlice";
import type { Notification } from "@/store/slices/notificationSlice";
import type { Booking } from "@/store/slices/bookingSlice";

// WebSocket URL - Connect directly to realtime-service (port 8006)
// WebSocket upgrade happens at browser level, cannot use Vite HTTP proxy
const WS_BASE_URL =
  import.meta.env.VITE_WS_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8006/ws`
    : "ws://localhost:8006/ws");

/**
 * WebSocket Message Format (Django Channels standard)
 */
export interface WebSocketMessage<T = unknown> {
  type: string;
  data: T;
}

/**
 * WebSocket Message Types
 */
export enum WSMessageType {
  // Parking slot updates
  SLOT_STATUS_UPDATE = "slot.status_update",
  ZONE_AVAILABILITY_UPDATE = "zone.availability_update",
  LOT_AVAILABILITY_UPDATE = "lot.availability_update",
  SLOTS_BATCH_UPDATE = "slots.batch_update",

  // Booking updates
  BOOKING_STATUS_UPDATE = "booking.status_update",
  BOOKING_CREATED = "booking.created",
  BOOKING_CANCELLED = "booking.cancelled",
  PARKING_COST_UPDATE = "parking.cost_update",

  // Notifications
  NOTIFICATION = "notification",

  // Incidents
  INCIDENT_REPORTED = "incident.reported",
  INCIDENT_RESOLVED = "incident.resolved",

  // System
  PING = "ping",
  PONG = "pong",
  ERROR = "error",
}

/**
 * WebSocket Service Class
 */
class WebSocketService {
  private socket: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000; // 3 seconds
  private pingIntervalTime = 30000; // 30 seconds
  private lastUserId: string | undefined = undefined;

  /**
   * Connect to WebSocket server
   */
  connect(userId?: string): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    if (userId !== undefined) {
      this.lastUserId = userId;
    }

    store.dispatch(setStatus("connecting"));

    const url = userId
      ? `${WS_BASE_URL}/user/${userId}/`
      : `${WS_BASE_URL}/parking/`;
    // Security: session cookie auth (short-lived token migration tracked in backlog)

    try {
      this.socket = new WebSocket(url);

      this.socket.onopen = this.handleOpen.bind(this);
      this.socket.onclose = this.handleClose.bind(this);
      this.socket.onerror = this.handleError.bind(this);
      this.socket.onmessage = this.handleMessage.bind(this);
    } catch (error) {
      this.reportError("connect", error);
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.clearTimers();

    if (this.socket) {
      this.socket.close(1000, "Client disconnect");
      this.socket = null;
    }

    store.dispatch(setStatus("disconnected"));
  }

  /**
   * Send message to server
   */
  send<T>(type: string, data: T): void {
    if (this.socket?.readyState !== WebSocket.OPEN) {
      this.reportError("send", new Error("socket_not_open"));
      return;
    }

    const message: WebSocketMessage<T> = { type, data };
    this.socket.send(JSON.stringify(message));
  }

  /**
   * Subscribe to a specific channel/room
   */
  subscribe(channel: string): void {
    this.send("subscribe", { channel });
  }

  /**
   * Unsubscribe from a channel/room
   */
  unsubscribe(channel: string): void {
    this.send("unsubscribe", { channel });
  }

  // Private handlers
  private handleOpen(): void {
    store.dispatch(setStatus("connected"));
    this.startPingInterval();
  }

  private handleClose(event: CloseEvent): void {
    this.clearTimers();

    if (event.code !== 1000) {
      // Abnormal closure - try to reconnect
      this.attemptReconnect();
    } else {
      store.dispatch(setStatus("disconnected"));
    }
  }

  private handleError(_event: Event): void {
    const readyState = this.socket?.readyState;
    this.reportError("socket_event", new Error(`ready_state:${readyState}`));
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      store.dispatch(setLastMessageAt(new Date().toISOString()));

      this.processMessage(message);
    } catch (error) {
      this.reportError("parse_message", error);
    }
  }

  /**
   * Process incoming WebSocket message and dispatch to Redux
   */
  private processMessage(message: WebSocketMessage): void {
    const { type, data } = message;

    switch (type) {
      // Parking slot updates
      case WSMessageType.SLOT_STATUS_UPDATE:
        store.dispatch(updateSlotStatus(data));
        break;

      case WSMessageType.ZONE_AVAILABILITY_UPDATE:
        store.dispatch(updateZoneAvailability(data));
        break;

      case WSMessageType.LOT_AVAILABILITY_UPDATE:
        store.dispatch(updateLotAvailability(data));
        break;

      case WSMessageType.SLOTS_BATCH_UPDATE:
        store.dispatch(batchUpdateSlots(data.slots || data));
        break;

      // Booking updates
      case WSMessageType.BOOKING_STATUS_UPDATE:
        store.dispatch(updateBookingStatus(data));
        break;

      case WSMessageType.BOOKING_CREATED:
        store.dispatch(addNewBooking(data as Booking));
        break;

      case WSMessageType.PARKING_COST_UPDATE:
        store.dispatch(updateCurrentParkingCost(data));
        break;

      // Notifications
      case WSMessageType.NOTIFICATION:
        store.dispatch(addNotification(data as Notification));
        break;

      // Incidents
      case WSMessageType.INCIDENT_REPORTED:
      case WSMessageType.INCIDENT_RESOLVED:
        // Add as notification
        store.dispatch(
          addNotification({
            id: Date.now().toString(),
            type: "incident",
            title:
              type === WSMessageType.INCIDENT_REPORTED
                ? "Sự cố mới"
                : "Sự cố đã xử lý",
            message: data.message || "",
            data,
            isRead: false,
            createdAt: new Date().toISOString(),
          }),
        );
        break;

      // System
      case WSMessageType.PONG:
        // Ping response received
        break;

      case WSMessageType.ERROR:
        store.dispatch(setError(data.message || "Lỗi từ server"));
        break;

      default:
        break;
    }
  }

  private attemptReconnect(): void {
    const { reconnectAttempts } = store.getState().websocket;

    if (reconnectAttempts >= this.maxReconnectAttempts) {
      store.dispatch(setError("Không thể kết nối lại sau nhiều lần thử"));
      store.dispatch(setStatus("error"));
      return;
    }

    store.dispatch(setStatus("reconnecting"));
    store.dispatch(incrementReconnectAttempts());

    const delay = this.reconnectDelay * Math.pow(2, reconnectAttempts); // Exponential backoff

    this.reconnectTimeout = setTimeout(() => {
      this.connect(this.lastUserId);
    }, delay);
  }

  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      this.send(WSMessageType.PING, { timestamp: Date.now() });
    }, this.pingIntervalTime);
  }

  private clearTimers(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private reportError(context: string, error: unknown): void {
    const message = error instanceof Error ? error.message : "unknown_error";
    store.dispatch(setError(`WebSocket error (${context}): ${message}`));
    console.error("[WebSocketService]", { context, message });
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();

/**
 * React hook for WebSocket connection management
 */
export function useWebSocket(userId?: string) {
  const connect = () => websocketService.connect(userId);
  const disconnect = () => websocketService.disconnect();
  const send = <T>(type: string, data: T) => websocketService.send(type, data);
  const subscribe = (channel: string) => websocketService.subscribe(channel);
  const unsubscribe = (channel: string) =>
    websocketService.unsubscribe(channel);

  return { connect, disconnect, send, subscribe, unsubscribe };
}
