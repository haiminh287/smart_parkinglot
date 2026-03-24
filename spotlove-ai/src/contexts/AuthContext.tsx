/**
 * Auth Context - Now using Redux for state management
 * This context provides a simpler interface to the Redux auth state
 * for backward compatibility with existing components
 */

import { ReactNode, useEffect, useRef } from "react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  login as loginAction,
  loginWithGoogle as loginWithGoogleAction,
  loginWithFacebook as loginWithFacebookAction,
  register as registerAction,
  logout as logoutAction,
  updateProfile as updateProfileAction,
} from "@/store/slices/authSlice";
import type { User, UserRole } from "@/store/slices/authSlice";
import { AuthContext } from "@/contexts/auth-context";

// Re-export types for backward compatibility
export type { User, UserRole };

export function AuthProvider({ children }: { children: ReactNode }) {
  const dispatch = useAppDispatch();
  const { user, isAuthenticated, isLoading } = useAppSelector(
    (state) => state.auth,
  );
  const initAttempted = useRef(false);

  // Initialize auth - verify session on mount (run ONCE only)
  useEffect(() => {
    if (initAttempted.current) return;
    initAttempted.current = true;
    import("@/store/slices/authSlice").then(({ initAuth }) => {
      dispatch(initAuth());
    });
  }, [dispatch]);

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
