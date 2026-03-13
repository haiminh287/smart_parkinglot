/**
 * useAuth Hook
 * Provides authentication functionality using Redux store
 */

import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  login as loginAction,
  loginWithGoogle as loginWithGoogleAction,
  loginWithFacebook as loginWithFacebookAction,
  register as registerAction,
  logout as logoutAction,
  fetchCurrentUser,
  updateProfile as updateProfileAction,
  clearError,
} from '@/store/slices/authSlice';
import type { User } from '@/store/slices/authSlice';

export function useAuth() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  
  const { user, isAuthenticated, isLoading, error } = useAppSelector(
    (state) => state.auth
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await dispatch(loginAction({ email, password }));
      if (loginAction.fulfilled.match(result)) {
        navigate('/');
      }
      return result;
    },
    [dispatch, navigate]
  );

  const loginWithGoogle = useCallback(async () => {
    const result = await dispatch(loginWithGoogleAction());
    if (loginWithGoogleAction.fulfilled.match(result)) {
      navigate('/');
    }
    return result;
  }, [dispatch, navigate]);

  const loginWithFacebook = useCallback(async () => {
    const result = await dispatch(loginWithFacebookAction());
    if (loginWithFacebookAction.fulfilled.match(result)) {
      navigate('/');
    }
    return result;
  }, [dispatch, navigate]);

  const register = useCallback(
    async (email: string, password: string, username: string) => {
      const result = await dispatch(registerAction({ email, password, username }));
      if (registerAction.fulfilled.match(result)) {
        navigate('/');
      }
      return result;
    },
    [dispatch, navigate]
  );

  const logout = useCallback(async () => {
    await dispatch(logoutAction());
    navigate('/login');
  }, [dispatch, navigate]);

  const checkAuth = useCallback(() => {
    return dispatch(fetchCurrentUser());
  }, [dispatch]);

  const updateProfile = useCallback(
    (data: Partial<User>) => {
      return dispatch(updateProfileAction(data));
    },
    [dispatch]
  );

  const clearAuthError = useCallback(() => {
    dispatch(clearError());
  }, [dispatch]);

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    isAdmin: user?.role === 'admin',
    login,
    loginWithGoogle,
    loginWithFacebook,
    register,
    logout,
    checkAuth,
    updateProfile,
    clearError: clearAuthError,
  };
}
