import { useAuthStore } from '@/lib/auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

interface RequestConfig extends RequestInit {
  skipAuth?: boolean;
}

// Keycloak rotates refresh tokens. All requests that expire together must
// share one refresh request; parallel refreshes with the same token can revoke
// the session and redirect the user while a form is being submitted.
let refreshInFlight: { token: string; promise: Promise<boolean> } | null = null;

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    const token = useAuthStore.getState().accessToken;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
  }

  async request<T>(endpoint: string, config: RequestConfig = {}): Promise<T> {
    const { skipAuth, ...fetchConfig } = config;
    const tokenUsed = skipAuth ? null : useAuthStore.getState().accessToken;
    const headers = skipAuth ? {} : await this.getAuthHeaders();

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...fetchConfig,
      headers: { ...headers, ...fetchConfig.headers },
    });

    if (response.status === 401 && tokenUsed) {
      // Another request may already have refreshed while this one was in
      // flight. Retry with the newer token instead of rotating twice.
      const currentToken = useAuthStore.getState().accessToken;
      const refreshed = currentToken && currentToken !== tokenUsed
        ? true
        : await this.refreshToken();
      if (refreshed) {
        const newHeaders = await this.getAuthHeaders();
        const retryToken = useAuthStore.getState().accessToken;
        const retryResponse = await fetch(`${this.baseUrl}${endpoint}`, {
          ...fetchConfig,
          headers: { ...newHeaders, ...fetchConfig.headers },
        });
        if (retryResponse.status === 401) {
          if (useAuthStore.getState().accessToken === retryToken) {
            useAuthStore.getState().expireSession();
          }
          throw new Error('Session expired');
        }
        if (!retryResponse.ok) throw await this.handleError(retryResponse);
        if (retryResponse.status === 204) return undefined as T;
        return retryResponse.json();
      }
      if (useAuthStore.getState().accessToken === tokenUsed) {
        useAuthStore.getState().expireSession();
      }
      throw new Error('Session expired');
    }

    if (!response.ok) throw await this.handleError(response);
    if (response.status === 204) return undefined as T;
    return response.json();
  }

  private async handleError(response: Response): Promise<Error> {
    try {
      const error = await response.json();
      if (Array.isArray(error.detail)) {
        const issue = error.detail[0];
        const field = Array.isArray(issue?.loc) ? issue.loc[issue.loc.length - 1] : undefined;
        if (typeof field === 'string' && typeof issue?.msg === 'string') {
          return new Error(`${field.replaceAll('_', ' ')}: ${issue.msg}`);
        }
      }
      const message = typeof error.detail === 'string' ? error.detail : error.message;
      return new Error(typeof message === 'string' ? message : `Request failed with status ${response.status}`);
    } catch {
      return new Error(`Request failed with status ${response.status}`);
    }
  }

  private refreshToken(): Promise<boolean> {
    const refreshToken = useAuthStore.getState().refreshToken;
    if (!refreshToken) return Promise.resolve(false);
    if (refreshInFlight?.token === refreshToken) return refreshInFlight.promise;

    const promise = this.performTokenRefresh(refreshToken).finally(() => {
      if (refreshInFlight?.promise === promise) {
        refreshInFlight = null;
      }
    });
    refreshInFlight = { token: refreshToken, promise };
    return promise;
  }

  private async performTokenRefresh(refreshToken: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;
      const data = await response.json();
      // Do not resurrect a session if the user logged out or signed in as a
      // different user while the refresh request was in flight.
      if (useAuthStore.getState().refreshToken !== refreshToken) return false;
      useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      return false;
    }
  }

  async get<T>(endpoint: string, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'GET' });
  }

  async post<T>(endpoint: string, body?: unknown, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'POST', body: body ? JSON.stringify(body) : undefined });
  }

  async put<T>(endpoint: string, body?: unknown, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'PUT', body: body ? JSON.stringify(body) : undefined });
  }

  async patch<T>(endpoint: string, body?: unknown, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'PATCH', body: body ? JSON.stringify(body) : undefined });
  }

  async delete<T>(endpoint: string, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'DELETE' });
  }

  async upload<T>(endpoint: string, formData: FormData, config?: RequestConfig): Promise<T> {
    const tokenUsed = config?.skipAuth ? null : useAuthStore.getState().accessToken;
    const headers = await this.getAuthHeaders();
    delete headers['Content-Type'];
    const requestConfig = {
      ...config,
      method: 'POST',
      headers: { ...headers, ...config?.headers },
      body: formData,
    };
    const response = await fetch(`${this.baseUrl}${endpoint}`, requestConfig);
    if (response.status === 401 && tokenUsed) {
      const currentToken = useAuthStore.getState().accessToken;
      const refreshed = currentToken && currentToken !== tokenUsed
        ? true
        : await this.refreshToken();
      if (refreshed) {
        const retryHeaders = await this.getAuthHeaders();
        delete retryHeaders['Content-Type'];
        const retryToken = useAuthStore.getState().accessToken;
        const retryResponse = await fetch(`${this.baseUrl}${endpoint}`, {
          ...requestConfig,
          headers: { ...retryHeaders, ...config?.headers },
        });
        if (retryResponse.status === 401 && useAuthStore.getState().accessToken === retryToken) {
          useAuthStore.getState().expireSession();
          throw new Error('Session expired');
        }
        if (!retryResponse.ok) throw await this.handleError(retryResponse);
        if (retryResponse.status === 204) return undefined as T;
        return retryResponse.json();
      }
      if (useAuthStore.getState().accessToken === tokenUsed) {
        useAuthStore.getState().expireSession();
      }
      throw new Error('Session expired');
    }
    if (!response.ok) throw await this.handleError(response);
    if (response.status === 204) return undefined as T;
    return response.json();
  }
}

export const api = new ApiClient(API_BASE);
