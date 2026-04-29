/**
 * Auth Business Service
 * Business logic layer - handles auth flow orchestration
 *
 * Pattern: service.ts = Business Logic + Redux Integration
 *          api.ts = Pure HTTP calls only
 */

import { authApi, handleAuthError } from "@/services/api/auth.api";
import { store } from "@/store";
import {
  setUser,
  clearError as clearAuthError,
} from "@/store/slices/authSlice";
import Cookies from "js-cookie";
import type { AxiosError } from "axios";
import type { ApiErrorResponse } from "@/services/api/axios.client";

// =====================
// Types
// =====================

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  username: string;
  phone?: string;
}

export interface AuthResult {
  success: boolean;
  message: string;
  redirectUrl?: string;
}

// =====================
// Auth Business Service
// =====================

export const authService = {
  /**
   * Login with credentials
   * - Calls API
   * - Updates Redux state
   * - Persists user info to cookie
   */
  async login(credentials: LoginCredentials): Promise<AuthResult> {
    try {
      const response = await authApi.login(credentials);

      // Persist user info (Django session cookie is HTTP-only, set automatically)
      Cookies.set("user_info", JSON.stringify(response.user), { expires: 7 });

      // Update Redux
      store.dispatch(setUser(response.user));

      // Determine redirect based on role
      const redirectUrl =
        response.user.role === "admin" ? "/admin/dashboard" : "/";

      return {
        success: true,
        message: response.message,
        redirectUrl,
      };
    } catch (error) {
      const message = handleAuthError(error as AxiosError<ApiErrorResponse>);
      return { success: false, message };
    }
  },

  /**
   * Register new user
   */
  async register(data: RegisterData): Promise<AuthResult> {
    try {
      const response = await authApi.register(data);

      // Auto-login after registration
      Cookies.set("user_info", JSON.stringify(response.user), { expires: 7 });
      store.dispatch(setUser(response.user));

      return {
        success: true,
        message: response.message,
        redirectUrl: "/",
      };
    } catch (error) {
      const message = handleAuthError(error as AxiosError<ApiErrorResponse>);
      return { success: false, message };
    }
  },

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    try {
      await authApi.logout();
    } catch (error) {
      console.error("Logout API failed:", error);
    } finally {
      // Always clear local state
      Cookies.remove("user_info");
      store.dispatch(setUser(null));
    }
  },

  /**
   * Initiate Google OAuth flow
   */
  async initiateGoogleAuth(): Promise<AuthResult> {
    try {
      const authUrl = await authApi.getGoogleAuthUrl();
      window.location.href = authUrl;
      return { success: true, message: "Redirecting to Google..." };
    } catch (error) {
      const message = handleAuthError(error as AxiosError<ApiErrorResponse>);
      return { success: false, message };
    }
  },

  /**
   * Initiate Facebook OAuth flow
   */
  async initiateFacebookAuth(): Promise<AuthResult> {
    try {
      const authUrl = await authApi.getFacebookAuthUrl();
      window.location.href = authUrl;
      return { success: true, message: "Redirecting to Facebook..." };
    } catch (error) {
      const message = handleAuthError(error as AxiosError<ApiErrorResponse>);
      return { success: false, message };
    }
  },

  /**
   * Restore session from cookie (on app load)
   */
  async restoreSession(): Promise<boolean> {
    try {
      const userInfoCookie = Cookies.get("user_info");
      if (!userInfoCookie) return false;

      // Verify with backend
      const response = await authApi.getCurrentUser();
      store.dispatch(setUser(response.user));
      return true;
    } catch (error) {
      // Session expired or invalid
      Cookies.remove("user_info");
      return false;
    }
  },

  /**
   * Change password
   */
  async changePassword(
    currentPassword: string,
    newPassword: string,
  ): Promise<AuthResult> {
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      return { success: true, message: "Mật khẩu đã được thay đổi" };
    } catch (error) {
      const message = handleAuthError(error as AxiosError<ApiErrorResponse>);
      return { success: false, message };
    }
  },

  /**
   * Clear auth errors
   */
  clearError(): void {
    store.dispatch(clearAuthError());
  },

  // =====================
  // Raw API Wrappers (for Store Thunks)
  // These methods just call API without Redux side effects,
  // allowing thunks to handle state updates via extraReducers.
  // =====================

  /**
   * Login (raw API call)
   * For use by Redux async thunks
   */
  async loginRaw(credentials: LoginCredentials) {
    return authApi.login(credentials);
  },

  /**
   * Register (raw API call)
   * For use by Redux async thunks
   */
  async registerRaw(data: RegisterData) {
    return authApi.register(data);
  },

  /**
   * Logout (raw API call)
   * For use by Redux async thunks
   */
  async logoutRaw() {
    return authApi.logout();
  },

  /**
   * Get current user (raw API call)
   * For use by Redux async thunks
   */
  async getCurrentUserRaw() {
    return authApi.getCurrentUser();
  },

  /**
   * Get Google OAuth URL (raw API call)
   * For use by Redux async thunks
   */
  async getGoogleAuthUrlRaw() {
    return authApi.getGoogleAuthUrl();
  },

  /**
   * Get Facebook OAuth URL (raw API call)
   * For use by Redux async thunks
   */
  async getFacebookAuthUrlRaw() {
    return authApi.getFacebookAuthUrl();
  },

  /**
   * Update user profile (raw API call)
   * For use by Redux async thunks
   * Note: Uses auth/me endpoint directly since no dedicated profile endpoint exists
   */
  async updateProfileRaw(data: {
    username?: string;
    phone?: string;
    address?: string;
  }) {
    // Import apiClient dynamically to avoid circular deps
    const { default: apiClient } = await import("@/services/api/axios.client");
    const response = await apiClient.patch("/auth/me/", data);
    return response.data;
  },
};
