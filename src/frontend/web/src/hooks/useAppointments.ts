'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type { Appointment, PaginatedResponse } from '@/types';

export interface CreateAppointmentInput {
  patient_id: string;
  patient_name?: string;
  patient_phone?: string;
  provider_id?: string;
  provider_name?: string;
  department?: string;
  appointment_type: 'general' | 'follow_up' | 'emergency' | 'specialist' | 'maternity' | 'immunization' | 'lab' | 'imaging' | 'telemedicine' | 'home_visit' | 'antenatal' | 'postnatal' | 'hiv' | 'tb' | 'mental_health';
  appointment_date: string;
  start_time: string;
  end_time: string;
  duration_minutes?: number;
  reason?: string;
  notes?: string;
  facility_id?: string;
  location?: string;
}

export function useAppointments(params?: { patientId?: string; providerId?: string; status?: string; date?: string; page?: number }) {
  const queryParams = new URLSearchParams();
  if (params?.patientId) queryParams.set('patient_id', params.patientId);
  if (params?.providerId) queryParams.set('provider_id', params.providerId);
  if (params?.status) queryParams.set('status', params.status);
  if (params?.date) queryParams.set('date', params.date);
  if (params?.page) queryParams.set('page', String(params.page));

  return useQuery<PaginatedResponse<Appointment>>({
    queryKey: ['appointments', params],
    queryFn: () => api.get(`/appointments?${queryParams.toString()}`),
  });
}

export function useAppointment(id: string) {
  return useQuery<Appointment>({
    queryKey: ['appointment', id],
    queryFn: () => api.get(`/appointments/${id}`),
    enabled: !!id,
  });
}

export function useCreateAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateAppointmentInput) => api.post('/appointments', data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['appointments'] }); },
  });
}

export function useUpdateAppointmentStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.patch(`/appointments/${id}/status`, { status }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['appointments'] }); },
  });
}

export function useTodayAppointments() {
  const today = new Date().toISOString().split('T')[0];
  return useAppointments({ date: today });
}
