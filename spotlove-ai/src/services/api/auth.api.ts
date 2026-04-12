/**
 * Auth API Service
 * API calls for authentication using Axios with HTTP-only cookies
 */

import apiClient, {
  extractErrorMessage,
  type ApiErrorResponse,
} from "./axios.client";
import type { AxiosError } from "axios";

// =====================
// Types
// =====================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: {
    id: string;
    email: string;
    username: string;
    avatar?: string;
    phone?: string;
    address?: string;
    role: "user" | "admin";
  };
  message: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  username: string;
  phone?: string;
}

export interface RegisterResponse {
  user: {
    id: string;
    email: string;
    username: string;
    role: "user" | "admin";
  };
  message: string;
}

export interface OAuthUrlResponse {
  authorization_url: string;
}

// =====================
// API Endpoints
// =====================

export const authApi = {
  /**
   * Login with email and password
   * Django will set HTTP-only cookie for session
   */
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>("/auth/login/", data);
    return response.data;
  },

  /**
   * Register new user
   */
  register: async (data: RegisterRequest): Promise<RegisterResponse> => {
    const response = await apiClient.post<RegisterResponse>(
      "/auth/register/",
      data,
    );
    return response.data;
  },

  /**
   * Logout - Django will clear HTTP-only cookie
   */
  logout: async (): Promise<void> => {
    await apiClient.post("/auth/logout/");
  },

  /**
   * Get Google OAuth2 authorization URL
   */
  getGoogleAuthUrl: async (): Promise<string> => {
    const response = await apiClient.get<OAuthUrlResponse>("/auth/google/");
    return response.data.authorization_url;
  },

  /**
   * Get Facebook OAuth2 authorization URL
   */
  getFacebookAuthUrl: async (): Promise<string> => {
    const response = await apiClient.get<OAuthUrlResponse>("/auth/facebook/");
    return response.data.authorization_url;
  },

  /**
   * Get current user info (uses session cookie)
   * Backend returns user object directly, not wrapped in { user: {...} }
   */
  getCurrentUser: async (): Promise<LoginResponse> => {
    const response = await apiClient.get("/auth/me/");

    const contentType =
      (response.headers?.["content-type"] as string | undefined) || "";

    if (!contentType.toLowerCase().includes("application/json")) {
      throw new Error("AUTH_ME_INVALID_CONTENT_TYPE");
    }

    // Backend returns user object directly, wrap it for consistency
    return { user: response.data, message: "Current user fetched" };
  },

  /**
   * Change password
   */
  changePassword: async (data: {
    current_password: string;
    new_password: string;
  }): Promise<void> => {
    await apiClient.post("/auth/change-password/", data);
  },

  /**
   * Request password reset
   */
  forgotPassword: async (email: string): Promise<void> => {
    await apiClient.post("/auth/forgot-password/", { email });
  },

  /**
   * Reset password with token
   */
  resetPassword: async (data: {
    token: string;
    new_password: string;
  }): Promise<void> => {
    await apiClient.post("/auth/reset-password/", data);
  },
};

// =====================
// Helper Functions
// =====================

/**
 * Handle auth API error and return user-friendly message
 */
export function handleAuthError(error: AxiosError<ApiErrorResponse>): string {
  return extractErrorMessage(error);
}
