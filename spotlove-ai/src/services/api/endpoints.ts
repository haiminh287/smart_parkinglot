/**
 * API Endpoints Configuration
 * Centralized endpoint definitions for all API calls
 */

export const ENDPOINTS = {
  // =====================
  // AUTH & USER
  // =====================
  AUTH: {
    LOGIN: "/auth/login/",
    REGISTER: "/auth/register/",
    LOGOUT: "/auth/logout/",
    GOOGLE: "/auth/google/",
    FACEBOOK: "/auth/facebook/",
    ME: "/auth/me/",
    CHANGE_PASSWORD: "/auth/change-password/",
    FORGOT_PASSWORD: "/auth/forgot-password/",
    RESET_PASSWORD: "/auth/reset-password/",
  },

  // USER: Not yet implemented in backend
  // USER: {
  //   PROFILE: '/users/profile/',
  //   UPDATE_PROFILE: '/users/profile/',
  //   AVATAR: '/users/avatar/',
  // },

  // =====================
  // VEHICLES
  // =====================
  VEHICLES: {
    LIST: "/vehicles/",
    CREATE: "/vehicles/",
    DETAIL: (id: string) => `/vehicles/${id}/`,
    UPDATE: (id: string) => `/vehicles/${id}/`,
    DELETE: (id: string) => `/vehicles/${id}/`,
    SET_DEFAULT: (id: string) => `/vehicles/${id}/set-default/`,
  },

  // =====================
  // PARKING LOTS & INFRASTRUCTURE
  // =====================
  PARKING_LOTS: {
    LIST: "/parking/lots/",
    DETAIL: (id: string) => `/parking/lots/${id}/`,
    NEARBY: "/parking/lots/nearby/",
    SEARCH: "/parking/lots/search/",
  },

  FLOORS: {
    LIST: "/parking/floors/",
    DETAIL: (floorId: string) => `/parking/floors/${floorId}/`,
  },

  ZONES: {
    LIST: "/parking/zones/",
    DETAIL: (zoneId: string) => `/parking/zones/${zoneId}/`,
    AVAILABLE_SLOTS: (zoneId: string) =>
      `/parking/zones/${zoneId}/available-slots/`,
  },

  SLOTS: {
    LIST: "/parking/slots/",
    DETAIL: (slotId: string) => `/parking/slots/${slotId}/`,
    STATUS: (slotId: string) => `/parking/slots/${slotId}/status/`,
  },

  // =====================
  // BOOKINGS
  // =====================
  BOOKINGS: {
    LIST: "/bookings/",
    CREATE: "/bookings/",
    DETAIL: (id: string) => `/bookings/${id}/`,
    CANCEL: (id: string) => `/bookings/${id}/cancel/`,
    HISTORY: "/bookings/",
    UPCOMING: "/bookings/upcoming/",
    CURRENT: "/bookings/current-parking/",
    CHECK_IN: (id: string) => `/bookings/${id}/checkin/`,
    CHECK_OUT: (id: string) => `/bookings/${id}/checkout/`,
    EXTEND: (id: string) => `/bookings/${id}/extend/`,
    QR_CODE: (id: string) => `/bookings/${id}/qr-code/`,
    STATS: "/bookings/stats/",
    PACKAGE_PRICING: "/bookings/packagepricings/",
  },

  // =====================
  // PAYMENTS
  // =====================
  PAYMENTS: {
    INITIATE: "/bookings/payment/",
    VERIFY: "/bookings/payment/verify/",
  },

  // =====================
  // CAMERAS & SECURITY
  // =====================
  CAMERAS: {
    LIST: "/parking/cameras/",
    DETAIL: (id: string) => `/parking/cameras/${id}/`,
    STREAM_URL: (id: string) => `/parking/cameras/${id}/stream/`,
  },

  // =====================
  // INCIDENTS & PANIC
  // =====================
  INCIDENTS: {
    LIST: "/incidents/",
    CREATE: "/incidents/",
    DETAIL: (id: string) => `/incidents/${id}/`,
    MY_INCIDENTS: "/incidents/my/",
    NEARBY_CAMERA: "/incidents/nearby-camera/",
    RESOLVE: (id: string) => `/incidents/${id}/resolve/`,
    CANCEL: (id: string) => `/incidents/${id}/cancel/`,
  },

  // =====================
  // MAP & NAVIGATION
  // =====================
  // MAP: Not yet implemented in backend
  // MAP: {
  //   NODES: (floorId: string) => `/floors/${floorId}/map/nodes/`,
  //   EDGES: (floorId: string) => `/floors/${floorId}/map/edges/`,
  //   DIRECTIONS: '/map/directions/',
  //   FLOOR_MAP: (floorId: string) => `/floors/${floorId}/map/`,
  // },

  // =====================
  // SUPPORT & CHAT
  // =====================
  // SUPPORT: Not yet implemented in backend
  // SUPPORT: {
  //   SEND_MESSAGE: '/support/messages/',
  //   MESSAGES: '/support/messages/',
  //   AI_CHAT: '/support/ai-chat/',
  //   TICKETS: '/support/tickets/',
  //   CREATE_TICKET: '/support/tickets/',
  // },

  // =====================
  // ADMIN
  // =====================
  ADMIN: {
    DASHBOARD_STATS: "/auth/admin/dashboard/stats/",
    USERS: {
      LIST: "/auth/admin/users/",
      DETAIL: (id: string) => `/auth/admin/users/${id}/`,
      DEACTIVATE: (id: string) => `/auth/admin/users/${id}/deactivate/`,
      ACTIVATE: (id: string) => `/auth/admin/users/${id}/activate/`,
      RESET_NO_SHOW: (id: string) => `/auth/admin/users/${id}/reset-no-show/`,
    },
  },

  // =====================
  // AI & SMART FEATURES
  // =====================
  AI: {
    DETECT_BANKNOTE: "/ai/detect/banknote/",
    SCAN_PLATE: "/ai/parking/scan-plate/",
    CHECK_IN: "/ai/parking/check-in/",
    CHECK_OUT: "/ai/parking/check-out/",
    ESP32_CHECK_IN: "/ai/parking/esp32/check-in/",
    ESP32_CHECK_OUT: "/ai/parking/esp32/check-out/",
    ESP32_VERIFY_SLOT: "/ai/parking/esp32/verify-slot/",
    ESP32_CASH_PAYMENT: "/ai/parking/esp32/cash-payment/",
  },

  // =====================
  // CALENDAR INTEGRATION
  // =====================
  // CALENDAR: Not yet implemented in backend
  // CALENDAR: {
  //   CONNECT_GOOGLE: '/calendar/google/connect/',
  //   CONNECT_APPLE: '/calendar/apple/connect/',
  //   DISCONNECT: (provider: string) => `/calendar/${provider}/disconnect/`,
  //   EVENTS: '/calendar/events/',
  //   AUTO_HOLD_SETTINGS: '/calendar/auto-hold/',
  // },
} as const;
