import { useAuthStore } from '@/lib/auth';

export async function clinicalApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = useAuthStore.getState().accessToken;
  if (!token) throw new Error('Please sign in to continue.');
  const response = await fetch(`/api/v1/${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers },
    cache: 'no-store',
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map((item: { msg: string }) => item.msg).join('; ') : `Request failed (${response.status})`);
  }
  return data as T;
}
