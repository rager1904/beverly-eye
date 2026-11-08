import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, UserRole } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  hasHydrated: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithKeycloak: () => void;
  logout: () => Promise<void>;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: User) => void;
  hasRole: (roles: UserRole | UserRole[]) => boolean;
  handleKeycloakCallback: (code: string) => Promise<void>;
  fetchUserProfile: () => Promise<void>;
  expireSession: () => void;
  setHasHydrated: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      hasHydrated: false,

      setHasHydrated: (hasHydrated: boolean) => set({ hasHydrated }),

      expireSession: () => set({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
      }),

      login: async (email: string, password: string) => {
        set({ isLoading: true });
        try {
          const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          });
          if (!response.ok) throw new Error('Invalid credentials');
          const tokens = await response.json();
          set({
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
          await get().fetchUserProfile();
          if (!get().user) throw new Error('Unable to load user profile');
        } catch (error) {
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
          });
          throw error;
        }
      },

      loginWithKeycloak: () => {
        const keycloakUrl = process.env.NEXT_PUBLIC_KEYCLOAK_URL || 'http://localhost:8080';
        const realm = process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'ubuntucare';
        const clientId = process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || 'frontend';
        const redirectUri = `${window.location.origin}/auth/callback`;
        const authUrl = `${keycloakUrl}/realms/${realm}/protocol/openid-connect/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=openid%20profile%20email%20roles&kc_idp_hint=`;
        window.location.href = authUrl;
      },

      logout: async () => {
        const { refreshToken } = get();
        get().expireSession();
        if (refreshToken) {
          try {
            await fetch(`${API_BASE}/auth/logout`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ refresh_token: refreshToken }),
              keepalive: true,
            });
          } catch {
            // Local logout must not wait for the authentication service.
          }
        }
      },

      setTokens: (access: string, refresh: string) => {
        set({ accessToken: access, refreshToken: refresh, isAuthenticated: true });
      },

      setUser: (user: User) => set({ user }),

      hasRole: (roles: UserRole | UserRole[]) => {
        const user = get().user;
        if (!user) return false;
        const roleList = Array.isArray(roles) ? roles : [roles];
        return roleList.includes(user.role);
      },

      handleKeycloakCallback: async (code: string) => {
        set({ isLoading: true });
        try {
          const keycloakUrl = process.env.NEXT_PUBLIC_KEYCLOAK_URL || 'http://localhost:8080';
          const realm = process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'ubuntucare';
          const clientId = process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || 'frontend';
          const redirectUri = `${window.location.origin}/auth/callback`;
          const response = await fetch(`${keycloakUrl}/realms/${realm}/protocol/openid-connect/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
              client_id: clientId,
              code,
              redirect_uri: redirectUri,
              grant_type: 'authorization_code',
            }),
          });
          if (!response.ok) throw new Error('Authentication failed');
          const tokens = await response.json();
          set({
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
          await get().fetchUserProfile();
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      fetchUserProfile: async () => {
        try {
          const { accessToken } = get();
          if (!accessToken) return;
          set({ isLoading: true });
          const response = await fetch(`${API_BASE}/auth/me`, {
            headers: { Authorization: `Bearer ${accessToken}` },
          });
          if (response.ok) {
            const profile = await response.json();
            set({
              user: {
                id: profile.id,
                email: profile.email,
                name: profile.name || profile.email,
                role: profile.role || 'patient',
                preferred_language: profile.preferred_language || 'en',
                email_verified: profile.email_verified || false,
                mfa_enabled: false,
                created_at: profile.created_at || new Date().toISOString(),
              },
              isAuthenticated: true,
              isLoading: false,
            });
          } else {
            get().expireSession();
            throw new Error(response.status === 401 ? 'Session expired' : 'Unable to load user profile');
          }
        } catch (error) {
          get().expireSession();
          throw error;
        }
      },
    }),
    {
      name: 'ubuntucare-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      skipHydration: true,
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
