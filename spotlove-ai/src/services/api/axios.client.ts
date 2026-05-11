/**
 * Axios API Client
 * Configured for Django OAuth2 with HTTP-only cookies
 */

import axios, {
  AxiosInstance,
  AxiosError,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from "axios";
import webLogger from "@/lib/webLogger";

declare module "axios" {
  interface InternalAxiosRequestConfig {
    metadata?: { startTime: number };
  }
}

// Base URL
// - Dev: default /api để đi qua Vite proxy
// - Prod: nếu VITE_API_URL là domain API trần (không có /api) thì tự append /api
const rawApiUrl =
  (import.meta.env.VITE_API_URL as string | undefined)?.trim() || "/api";
const BASE_URL = (() => {
  if (rawApiUrl === "/api") return rawApiUrl;

  const normalized = rawApiUrl.replace(/\/+$/, "");
  const lower = normalized.toLowerCase();

  if (lower.endsWith("/api")) {
    return normalized;
  }

  return `${normalized}/api`;
})();

/**
 * Create Axios instance with default config
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

/**
 * Request interceptor
 * - Add CSRF token if available
 * - Add any custom headers
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get CSRF token from cookie if exists (Django CSRF protection)
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) {
      config.headers["X-CSRFToken"] = csrfToken;
    }

    // Track request start time for duration calculation
    config.metadata = { startTime: Date.now() };

    // Log every outgoing request
    webLogger.apiReq(
      config.method ?? "GET",
      config.url ?? "",
      config.data
        ? typeof config.data === "string"
          ? JSON.parse(config.data)
          : config.data
        : undefined,
    );

    return config;
  },
  (error: AxiosError) => {
    webLogger.error("REQ", "Request setup failed", { message: error.message });
    return Promise.reject(error);
  },
);

/**
 * Response interceptor
 * - Log all responses and errors
 * - Let Redux handle 401/403 (don't redirect here)
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const cfg = response.config;
    const duration = cfg.metadata?.startTime
      ? Date.now() - cfg.metadata.startTime
      : 0;
    webLogger.apiRes(
      cfg.method ?? "GET",
      cfg.url ?? "",
      response.status,
      duration,
      response.data,
    );
    return response;
  },
  async (error: AxiosError) => {
    const cfg = error.config ?? ({} as InternalAxiosRequestConfig);
    const duration = cfg.metadata?.startTime
      ? Date.now() - cfg.metadata.startTime
      : 0;

    if (error.response) {
      webLogger.apiErr(
        cfg.method ?? "GET",
        cfg.url ?? "",
        error.response.status,
        duration,
        error.response.data,
      );
      console.warn(`API Error ${error.response.status}:`, {
        url: error.config?.url,
        method: error.config?.method,
        status: error.response.status,
        data: error.response.data,
      });
    } else if (error.request) {
      webLogger.error("NET", "Network error — no response", {
        url: cfg.url,
        message: error.message,
      });
      console.error("Network error - no response:", error.message);
    } else {
      webLogger.error("REQ", "Request error", { message: error.message });
    }

    // Don't auto-redirect on 401/403 - let Redux authSlice handle it
    return Promise.reject(error);
  },
);

/**
 * Helper function to get cookie value
 */
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(";").shift() || null;
  }
  return null;
}

/**
 * Django REST Framework Pagination Response
 */
export interface DjangoPaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Standard API Response
 */
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

/**
 * API Error Response
 */
export interface ApiErrorResponse {
  detail?: string;
  message?: string;
  errors?: Record<string, string[]>;
  non_field_errors?: string[];
}

/**
 * Pagination params for Django REST
 */
export interface PaginationParams {
  page?: number;
  pageSize?: number; // Frontend uses camelCase
  ordering?: string;
  search?: string;
}

/**
 * Build query params for Django REST pagination
 */
export function buildPaginationParams(
  params: PaginationParams,
): Record<string, string> {
  const queryParams: Record<string, string> = {};

  if (params.page) queryParams.page = String(params.page);
  if (params.pageSize) queryParams.page_size = String(params.pageSize); // Convert to snake_case for Django
  if (params.ordering) queryParams.ordering = params.ordering;
  if (params.search) queryParams.search = params.search;

  return queryParams;
}

/**
 * Extract error message from API error response
 */
export function extractErrorMessage(
  error: AxiosError<ApiErrorResponse>,
): string {
  if (error.response?.data) {
    const data = error.response.data;

    // Check different error formats
    if (data.detail) return data.detail;
    if (data.message) return data.message;
    if (data.non_field_errors?.length) return data.non_field_errors[0];

    // Check field-specific errors
    if (data.errors) {
      const firstField = Object.keys(data.errors)[0];
      if (firstField && data.errors[firstField]?.length) {
        return data.errors[firstField][0];
      }
    }
  }

  // Default error messages by status code
  switch (error.response?.status) {
    case 400:
      return "Dữ liệu không hợp lệ";
    case 401:
      return "Vui lòng đăng nhập lại";
    case 403:
      return "Bạn không có quyền thực hiện thao tác này";
    case 404:
      return "Không tìm thấy dữ liệu";
    case 500:
      return "Lỗi hệ thống, vui lòng thử lại sau";
    default:
      return "Có lỗi xảy ra, vui lòng thử lại";
  }
}

export default apiClient;
