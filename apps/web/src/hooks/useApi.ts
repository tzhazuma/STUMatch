import { useCallback } from 'react';
import apiClient from '@/api/client';

export function useApi() {
  const get = useCallback(async <T>(url: string, params?: Record<string, unknown>) => {
    const res = await apiClient.get<{ data: T }>(url, { params });
    return res.data.data;
  }, []);

  const post = useCallback(async <T>(url: string, data?: Record<string, unknown>) => {
    const res = await apiClient.post<{ data: T }>(url, data);
    return res.data.data;
  }, []);

  const put = useCallback(async <T>(url: string, data?: Record<string, unknown>) => {
    const res = await apiClient.put<{ data: T }>(url, data);
    return res.data.data;
  }, []);

  const del = useCallback(async <T>(url: string) => {
    const res = await apiClient.delete<{ data: T }>(url);
    return res.data.data;
  }, []);

  return { get, post, put, del };
}
