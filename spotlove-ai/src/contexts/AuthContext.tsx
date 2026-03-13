/**
 * Auth Context - Now using Redux for state management
 * This context provides a simpler interface to the Redux auth state
 * for backward compatibility with existing components
 */

import { createContext, useContext, ReactNode, useEffect } from "react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  login as loginAction,
  loginWithGoogle as loginWithGoogleAction,
  loginWithFacebook as loginWithFacebookAction,
  register as registerAction,
  logout as logoutAction,
  fetchCurrentUser,
  updateProfile as updateProfileAction,
} from "@/store/slices/authSlice";
import type { User, UserRole } from "@/store/slices/authSlice";

// Re-export types for backward compatibility
export type { User, UserRole };

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  loginWithFacebook: () => Promise<void>;
  register: (
    email: string,
    password: string,
    username: string,
  ) => Promise<void>;
  logout: () => void;
  updateProfile: (data: Partial<User>) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const dispatch = useAppDispatch();
  const { user, isAuthenticated, isLoading, error } = useAppSelector(
    (state) => state.auth,
  );

  // Initialize auth - verify session on mount
  useEffect(() => {
    // Only run initAuth if we don't already have user data
    // This prevents re-verification immediately after login
    if (!user && !isLoading) {
      // Import initAuth dynamically to avoid circular dependency
      import("@/store/slices/authSlice").then(({ initAuth }) => {
        dispatch(initAuth());
      });
    }
  }, [dispatch]); // Only run once on mount

  const login = async (email: string, password: string) => {
    const result = await dispatch(loginAction({ email, password }));
    if (loginAction.rejected.match(result)) {
      throw new Error(result.payload as string);
    }
  };

  const loginWithGoogle = async () => {
    const result = await dispatch(loginWithGoogleAction());
    if (loginWithGoogleAction.rejected.match(result)) {
      throw new Error(result.payload as string);
    }
  };

  const loginWithFacebook = async () => {
    const result = await dispatch(loginWithFacebookAction());
    if (loginWithFacebookAction.rejected.match(result)) {
      throw new Error(result.payload as string);
    }
  };

  const register = async (
    email: string,
    password: string,
    username: string,
  ) => {
    const result = await dispatch(
      registerAction({ email, password, username }),
    );
    if (registerAction.rejected.match(result)) {
      throw new Error(result.payload as string);
    }
  };

  const logout = () => {
    dispatch(logoutAction());
  };

  const updateProfile = async (data: Partial<User>) => {
    const result = await dispatch(updateProfileAction(data));
    if (updateProfileAction.rejected.match(result)) {
      throw new Error(result.payload as string);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoading,
        login,
        loginWithGoogle,
        loginWithFacebook,
        register,
        logout,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
