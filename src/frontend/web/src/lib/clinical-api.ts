import { api } from '@/lib/api-client';

export async function clinicalApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const endpoint = path.startsWith('/') ? path : `/${path}`;
  return api.request<T>(endpoint, {
    ...options,
    cache: 'no-store',
  });
}
