/**
 * Auth Slice
 * Manages user authentication state
 * Uses cookies for token storage (Django OAuth2 HTTP-only)
 */

import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import Cookies from "js-cookie";
import { authApi } from "@/services/api/auth.api";

export type UserRole = "user" | "admin";

export interface User {
  id: string;
  email: string;
  username: string;
  avatar?: string;
  phone?: string;
  address?: string;
  role: UserRole;
  isActive?: boolean;
  noShowCount?: number;
  forceOnlinePayment?: boolean;
  lastLogin?: string;
  dateJoined?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

interface ApiErrorPayload {
  response?: {
    status?: number;
    data?: {
      message?: string;
    };
  };
}

const getErrorMessage = (error: unknown, fallbackMessage: string): string => {
  const apiError = error as ApiErrorPayload;
  return apiError.response?.data?.message || fallbackMessage;
};

const getErrorStatus = (error: unknown): number | undefined => {
  const apiError = error as ApiErrorPayload;
  return apiError.response?.status;
};

// Try to restore user from cookie on app init
const getUserFromCookie = (): User | null => {
  try {
    const userInfo = Cookies.get("user_info");
    // Check if userInfo exists and is not "undefined" string
    if (userInfo && userInfo !== "undefined") {
      return JSON.parse(userInfo);
    }
  } catch (error) {
    console.error("Failed to parse user cookie:", error);
    Cookies.remove("user_info");
  }
  return null;
};

const initialState: AuthState = {
  user: getUserFromCookie(),
  isAuthenticated: !!getUserFromCookie(),
  isLoading: false,
  error: null,
};

// Async thunks
export const login = createAsyncThunk(
  "auth/login",
  async (
    credentials: { email: string; password: string },
    { rejectWithValue },
  ) => {
    try {
      const response = await authApi.login(credentials);
      return response.user;
    } catch (error: unknown) {
      return rejectWithValue(getErrorMessage(error, "Đăng nhập thất bại"));
    }
  },
);

export const loginWithGoogle = createAsyncThunk(
  "auth/loginWithGoogle",
  async (_, { rejectWithValue }) => {
    try {
      window.location.href = await authApi.getGoogleAuthUrl();
      return null; // Will redirect to Google
    } catch (error: unknown) {
      return rejectWithValue(
        getErrorMessage(error, "Đăng nhập Google thất bại"),
      );
    }
  },
);

export const loginWithFacebook = createAsyncThunk(
  "auth/loginWithFacebook",
  async (_, { rejectWithValue }) => {
    try {
      window.location.href = await authApi.getFacebookAuthUrl();
      return null; // Will redirect to Facebook
    } catch (error: unknown) {
      return rejectWithValue(
        getErrorMessage(error, "Đăng nhập Facebook thất bại"),
      );
    }
  },
);

export const register = createAsyncThunk(
  "auth/register",
  async (
    data: { email: string; password: string; username: string },
    { rejectWithValue },
  ) => {
    try {
      const response = await authApi.register(data);
      return response.user;
    } catch (error: unknown) {
      return rejectWithValue(getErrorMessage(error, "Đăng ký thất bại"));
    }
  },
);

export const logout = createAsyncThunk(
  "auth/logout",
  async (_, { rejectWithValue }) => {
    try {
      await authApi.logout();
      Cookies.remove("user_info");
    } catch (error: unknown) {
      return rejectWithValue(getErrorMessage(error, "Đăng xuất thất bại"));
    }
  },
);

// Initialize auth - verify session validity with backend
export const initAuth = createAsyncThunk(
  "auth/initAuth",
  async (_, { rejectWithValue }) => {
    try {
      // Check if we have user info in cookie
      const userInfo = Cookies.get("user_info");
      if (!userInfo || userInfo === "undefined") {
        return rejectWithValue("No session found");
      }

      // Verify session with backend
      const response = await authApi.getCurrentUser();
      return response.user;
    } catch (error: unknown) {
      const status = getErrorStatus(error);

      // Only clear cookie if session is actually invalid (401/403)
      // Don't clear on network errors (500, timeout, etc)
      if (status === 401 || status === 403) {
        Cookies.remove("user_info");
        return rejectWithValue("Session expired");
      }

      // For network errors, keep existing cookie and try to use cached user
      const cachedUser = Cookies.get("user_info");
      if (cachedUser && cachedUser !== "undefined") {
        try {
          return JSON.parse(cachedUser);
        } catch {
          // If parsing fails, clear invalid cookie
          Cookies.remove("user_info");
        }
      }

      return rejectWithValue(getErrorMessage(error, "Network error"));
    }
  },
);

export const fetchCurrentUser = createAsyncThunk(
  "auth/fetchCurrentUser",
  async (_, { rejectWithValue }) => {
    try {
      const response = await authApi.getCurrentUser();
      return response.user;
    } catch (error: unknown) {
      return rejectWithValue(
        getErrorMessage(error, "Không thể lấy thông tin user"),
      );
    }
  },
);

export const updateProfile = createAsyncThunk(
  "auth/updateProfile",
  async (data: Partial<User>, { rejectWithValue }) => {
    try {
      // FE-BUG 14 FIX: Use real API call instead of mock
      const response = await authApi.getCurrentUser();
      // For now use auth/me endpoint for profile update until dedicated endpoint exists
      const { default: apiClient } =
        await import("@/services/api/axios.client");
      const updateResponse = await apiClient.patch("/auth/me/", data);
      const updatedUser = updateResponse.data;
      // Update cookie with non-sensitive data only
      Cookies.set(
        "user_info",
        JSON.stringify({
          id: updatedUser.id,
          username: updatedUser.username,
          role: updatedUser.role,
        }),
        { expires: 7 },
      );
      return updatedUser;
    } catch (error: unknown) {
      return rejectWithValue(getErrorMessage(error, "Cập nhật thất bại"));
    }
  },
);

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setUser: (state, action: PayloadAction<User | null>) => {
      state.user = action.payload;
      state.isAuthenticated = !!action.payload;
    },
  },
  extraReducers: (builder) => {
    // Login
    builder
      .addCase(login.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
        // FE-BUG 13 FIX: Store only non-sensitive data in cookie
        const safeUserInfo = {
          id: action.payload.id,
          username: action.payload.username,
          role: action.payload.role,
        };
        Cookies.set("user_info", JSON.stringify(safeUserInfo), {
          expires: 7,
        });
      })
      .addCase(login.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Login with Google
    builder
      .addCase(loginWithGoogle.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginWithGoogle.fulfilled, (state) => {
        // Redirecting to Google - don't set state
        state.isLoading = false;
      })
      .addCase(loginWithGoogle.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Login with Facebook
    builder
      .addCase(loginWithFacebook.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginWithFacebook.fulfilled, (state) => {
        // Redirecting to Facebook - don't set state
        state.isLoading = false;
      })
      .addCase(loginWithFacebook.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Register
    builder
      .addCase(register.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(register.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
        Cookies.set("user_info", JSON.stringify(action.payload), {
          expires: 7,
        });
      })
      .addCase(register.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Logout
    builder
      .addCase(logout.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(logout.fulfilled, (state) => {
        state.isLoading = false;
        state.user = null;
        state.isAuthenticated = false;
      })
      .addCase(logout.rejected, (state) => {
        state.isLoading = false;
        state.user = null;
        state.isAuthenticated = false;
      });

    // Initialize auth (verify session on app mount)
    builder
      .addCase(initAuth.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(initAuth.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
        // Update cookie with fresh data
        Cookies.set("user_info", JSON.stringify(action.payload), {
          expires: 7,
        });
      })
      .addCase(initAuth.rejected, (state, action) => {
        state.isLoading = false;

        // CRITICAL: Only clear auth if explicitly rejected with "Session expired" or "No session found"
        // Don't clear on network errors - preserve existing authentication state
        const errorMessage = action.payload as string;
        if (
          errorMessage === "Session expired" ||
          errorMessage === "No session found"
        ) {
          state.user = null;
          state.isAuthenticated = false;
          Cookies.remove("user_info");
        }
        // For other errors (network, timeout), keep existing auth state
        // User can retry or will be logged out on next successful API call that returns 401
      });

    // Fetch current user
    builder
      .addCase(fetchCurrentUser.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.isAuthenticated = !!action.payload;
        Cookies.set("user_info", JSON.stringify(action.payload), {
          expires: 7,
        });
      })
      .addCase(fetchCurrentUser.rejected, (state) => {
        state.isLoading = false;
        state.user = null;
        state.isAuthenticated = false;
      });

    // Update profile
    builder
      .addCase(updateProfile.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(updateProfile.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
      })
      .addCase(updateProfile.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const { clearError, setUser } = authSlice.actions;
export default authSlice.reducer;
