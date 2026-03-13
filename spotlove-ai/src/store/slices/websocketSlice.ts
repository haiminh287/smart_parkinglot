/**
 * WebSocket Slice
 * Manages WebSocket connection state
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

interface WebSocketState {
  status: ConnectionStatus;
  error: string | null;
  reconnectAttempts: number;
  lastMessageAt: string | null;
}

const initialState: WebSocketState = {
  status: 'disconnected',
  error: null,
  reconnectAttempts: 0,
  lastMessageAt: null,
};

const websocketSlice = createSlice({
  name: 'websocket',
  initialState,
  reducers: {
    setStatus: (state, action: PayloadAction<ConnectionStatus>) => {
      state.status = action.payload;
      if (action.payload === 'connected') {
        state.reconnectAttempts = 0;
        state.error = null;
      }
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      if (action.payload) {
        state.status = 'error';
      }
    },
    incrementReconnectAttempts: (state) => {
      state.reconnectAttempts += 1;
    },
    resetReconnectAttempts: (state) => {
      state.reconnectAttempts = 0;
    },
    setLastMessageAt: (state, action: PayloadAction<string>) => {
      state.lastMessageAt = action.payload;
    },
  },
});

export const {
  setStatus,
  setError,
  incrementReconnectAttempts,
  resetReconnectAttempts,
  setLastMessageAt,
} = websocketSlice.actions;

export default websocketSlice.reducer;
