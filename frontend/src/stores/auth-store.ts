/**
 * Auth Store
 * Manages authentication state with Zustand
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '@/lib/api-client';

interface User {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  
  // Actions
  setAuth: (user: User, token: string) => void;
  logout: () => void;
  initialize: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      
      setAuth: (user, token) => {
        // Update API client with token
        api.setAccessToken(token);
        
        set({
          user,
          accessToken: token,
          isAuthenticated: true,
        });
      },
      
      logout: () => {
        // Clear API client token
        api.setAccessToken(null);
        
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
        });
      },
      
      initialize: () => {
        // Called on app load to set token in API client
        const { accessToken } = get();
        if (accessToken) {
          api.setAccessToken(accessToken);
        }
      },
    }),
    {
      name: 'orbit-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
