import { useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import { API } from '../api/endpoints';

export function useAuth() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);
  const isHydrated = useAuthStore((state) => state.isHydrated);
  const setAuth = useAuthStore((state) => state.setAuth);
  const logout = useAuthStore((state) => state.logout);

  const login = useCallback(async (email: string, password: string) => {
    const data = await API.auth.login(email, password);
    setAuth(
      { access_token: data.access_token, refresh_token: data.refresh_token },
      data.user
    );
    return data;
  }, [setAuth]);

  const register = useCallback(
    async (payload: {
      email: string;
      code: string;
      password: string;
      nickname: string;
      school: string;
    }) => {
      const data = await API.auth.register(payload);
      setAuth(
        { access_token: data.access_token, refresh_token: data.refresh_token },
        data.user
      );
      return data;
    },
    [setAuth]
  );

  const handleLogout = useCallback(async () => {
    try {
      await API.auth.logout();
    } finally {
      logout();
    }
  }, [logout]);

  return {
    isAuthenticated: !!accessToken,
    user,
    isHydrated,
    login,
    register,
    logout: handleLogout,
  };
}
