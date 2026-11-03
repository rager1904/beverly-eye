import { useAuthStore } from '@/lib/auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

interface RequestConfig extends RequestInit {
  skipAuth?: boolean;
}

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

  private async request<T>(endpoint: string, config: RequestConfig = {}): Promise<T> {
    const { skipAuth, ...fetchConfig } = config;
    const headers = skipAuth ? {} : await this.getAuthHeaders();

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...fetchConfig,
      headers: { ...headers, ...fetchConfig.headers },
    });

    if (response.status === 401) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        const newHeaders = await this.getAuthHeaders();
        const retryResponse = await fetch(`${this.baseUrl}${endpoint}`, {
          ...fetchConfig,
          headers: { ...newHeaders, ...fetchConfig.headers },
        });
        if (!retryResponse.ok) throw await this.handleError(retryResponse);
        return retryResponse.json();
      }
      useAuthStore.getState().logout();
      throw new Error('Session expired');
    }

    if (!response.ok) throw await this.handleError(response);
    if (response.status === 204) return undefined as T;
    return response.json();
  }

  private async handleError(response: Response): Promise<Error> {
    try {
      const error = await response.json();
      return new Error(error.detail || error.message || `Request failed with status ${response.status}`);
    } catch {
      return new Error(`Request failed with status ${response.status}`);
    }
  }

  private async refreshToken(): Promise<boolean> {
    const refreshToken = useAuthStore.getState().refreshToken;
    if (!refreshToken) return false;
    try {
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;
      const data = await response.json();
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
    const headers = await this.getAuthHeaders();
    delete headers['Content-Type'];
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...config,
      method: 'POST',
      headers: { ...headers, ...config?.headers },
      body: formData,
    });
    if (!response.ok) throw await this.handleError(response);
    return response.json();
  }
}

export const api = new ApiClient(API_BASE);
