/**
 * useWebSocketConnection Hook
 * Manages WebSocket connection lifecycle with auto-connect on login
 */

import { useEffect, useCallback } from 'react';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { websocketService, WSMessageType } from '@/services/websocket.service';
import { resetReconnectAttempts } from '@/store/slices/websocketSlice';

export function useWebSocketConnection() {
  const dispatch = useAppDispatch();
  const { isAuthenticated, user } = useAppSelector((state) => state.auth);
  const { status, error, reconnectAttempts, lastMessageAt } = useAppSelector(
    (state) => state.websocket
  );

  // Connect to WebSocket when authenticated
  useEffect(() => {
    if (isAuthenticated && user?.id) {
      // Connect with user ID for personalized channel
      websocketService.connect(user.id);

      // Cleanup on unmount or logout
      return () => {
        websocketService.disconnect();
      };
    } else {
      // Disconnect if not authenticated
      websocketService.disconnect();
    }
  }, [isAuthenticated, user?.id]);

  // Manual reconnect
  const reconnect = useCallback(() => {
    dispatch(resetReconnectAttempts());
    if (user?.id) {
      websocketService.connect(user.id);
    }
  }, [dispatch, user?.id]);

  // Subscribe to a specific parking lot for slot updates
  const subscribeToParkingLot = useCallback((lotId: string) => {
    websocketService.subscribe(`parking.lot.${lotId}`);
  }, []);

  // Unsubscribe from parking lot
  const unsubscribeFromParkingLot = useCallback((lotId: string) => {
    websocketService.unsubscribe(`parking.lot.${lotId}`);
  }, []);

  // Subscribe to a specific zone for detailed slot updates
  const subscribeToZone = useCallback((zoneId: string) => {
    websocketService.subscribe(`parking.zone.${zoneId}`);
  }, []);

  // Unsubscribe from zone
  const unsubscribeFromZone = useCallback((zoneId: string) => {
    websocketService.unsubscribe(`parking.zone.${zoneId}`);
  }, []);

  // Subscribe to booking updates for a specific booking
  const subscribeToBooking = useCallback((bookingId: string) => {
    websocketService.subscribe(`booking.${bookingId}`);
  }, []);

  // Unsubscribe from booking
  const unsubscribeFromBooking = useCallback((bookingId: string) => {
    websocketService.unsubscribe(`booking.${bookingId}`);
  }, []);

  // Send custom message
  const send = useCallback(<T>(type: string, data: T) => {
    websocketService.send(type, data);
  }, []);

  return {
    // State
    isConnected: status === 'connected',
    isConnecting: status === 'connecting',
    isReconnecting: status === 'reconnecting',
    status,
    error,
    reconnectAttempts,
    lastMessageAt,
    
    // Actions
    reconnect,
    send,
    
    // Subscription helpers
    subscribeToParkingLot,
    unsubscribeFromParkingLot,
    subscribeToZone,
    unsubscribeFromZone,
    subscribeToBooking,
    unsubscribeFromBooking,
  };
}
