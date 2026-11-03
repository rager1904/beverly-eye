'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type { TelemedicineSession } from '@/types';

export function useTelemedicineSessions(params?: { providerId?: string; patientId?: string; status?: string }) {
  const queryParams = new URLSearchParams();
  if (params?.providerId) queryParams.set('provider_id', params.providerId);
  if (params?.patientId) queryParams.set('patient_id', params.patientId);
  if (params?.status) queryParams.set('status', params.status);

  return useQuery<TelemedicineSession[]>({
    queryKey: ['telemedicine-sessions', params],
    queryFn: () => api.get(`/telemedicine/sessions?${queryParams.toString()}`),
    refetchInterval: 10000,
  });
}

export function useStartSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { patient_id: string; provider_id: string }) => api.post('/telemedicine/sessions', data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['telemedicine-sessions'] }); },
  });
}

export function useEndSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => api.post(`/telemedicine/sessions/${sessionId}/end`),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['telemedicine-sessions'] }); },
  });
}

export function useWaitingRoom(facilityId: string) {
  return useQuery<TelemedicineSession[]>({
    queryKey: ['telemedicine-waiting', facilityId],
    queryFn: () => api.get(`/telemedicine/waiting-room/${facilityId}`),
    enabled: !!facilityId,
    refetchInterval: 5000,
  });
}
