import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Tokens } from '@/types';

interface AuthStore {
  access_token: string | null;
  refresh_token: string | null;
  token_type: string;
  expires_at: number;
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (payload: Tokens & { user: User }) => void;
  updateTokens: (payload: Tokens) => void;
  setUser: (user: User) => void;
  logout: () => void;
}

const emptyState = {
  access_token: null,
  refresh_token: null,
  token_type: 'bearer',
  expires_at: 0,
  user: null,
  isAuthenticated: false,
};

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      ...emptyState,
      setAuth: (payload) =>
        set({
          access_token: payload.access_token,
          refresh_token: payload.refresh_token,
          token_type: payload.token_type,
          expires_at: Date.now() + payload.expires_in * 1000,
          user: payload.user,
          isAuthenticated: true,
        }),
      updateTokens: (payload) =>
        set({
          access_token: payload.access_token,
          refresh_token: payload.refresh_token,
          token_type: payload.token_type,
          expires_at: Date.now() + payload.expires_in * 1000,
        }),
      setUser: (user) => set({ user }),
      logout: () => set({ ...emptyState }),
    }),
    {
      name: 'unimatch-auth',
      partialize: (state) => ({
        access_token: state.access_token,
        refresh_token: state.refresh_token,
        token_type: state.token_type,
        expires_at: state.expires_at,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
