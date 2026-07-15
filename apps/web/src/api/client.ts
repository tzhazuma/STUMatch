import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/store/authStore';
import { refreshAccessToken } from './endpoints';

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

const onRefreshed = (token: string) => {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
};

const addRefreshSubscriber = (cb: (token: string) => void) => {
  refreshSubscribers.push(cb);
};

apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const { access_token, expires_at, refresh_token } = useAuthStore.getState();

  if (access_token) {
    const isExpiringSoon = expires_at && Date.now() + 120_000 > expires_at;

    if (isExpiringSoon && refresh_token && !config.url?.includes('/auth/refresh')) {
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          const res = await refreshAccessToken(refresh_token);
          useAuthStore.getState().updateTokens(res);
          onRefreshed(res.access_token);
        } catch (e) {
          useAuthStore.getState().logout();
          window.location.href = '/login';
          throw e;
        } finally {
          isRefreshing = false;
        }
      } else {
        await new Promise<string>((resolve) => addRefreshSubscriber(resolve));
      }
    }

    config.headers.Authorization = `Bearer ${useAuthStore.getState().access_token}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const status = error.response?.status;

    if (status === 401 && originalRequest && !originalRequest._retry && !originalRequest.url?.includes('/auth/refresh')) {
      const { refresh_token, logout } = useAuthStore.getState();
      if (!refresh_token) {
        logout();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      originalRequest._retry = true;
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          const res = await refreshAccessToken(refresh_token);
          useAuthStore.getState().updateTokens(res);
          onRefreshed(res.access_token);
          return apiClient(originalRequest);
        } catch (e) {
          logout();
          window.location.href = '/login';
          return Promise.reject(e);
        } finally {
          isRefreshing = false;
        }
      }

      return new Promise((resolve) => {
        addRefreshSubscriber((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          resolve(apiClient(originalRequest));
        });
      });
    }

    return Promise.reject(error);
  }
);

export default apiClient;
