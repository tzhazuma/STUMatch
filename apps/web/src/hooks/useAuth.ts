import { useCallback } from 'react';
import { useAuthStore } from '@/store/authStore';
import { login as apiLogin, register as apiRegister, logout as apiLogout } from '@/api/endpoints';
import type { User } from '@/types';

export function useAuth() {
  const { user, isAuthenticated, access_token, expires_at, setAuth, setUser, logout } = useAuthStore();

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin({ email, password });
    setAuth(res);
    return res.user;
  }, [setAuth]);

  const registerAccount = useCallback(
    async (payload: { email: string; code: string; password: string; nickname: string; school: string; phone?: string }) => {
      const res = await apiRegister({ phone: payload.phone, ...payload });
      setAuth(res);
      return res.user;
    },
    [setAuth]
  );

  const doLogout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      logout();
    }
  }, [logout]);

  return {
    user,
    isAuthenticated,
    access_token,
    expires_at,
    login,
    register: registerAccount,
    logout: doLogout,
    setUser,
  } as const;
}
