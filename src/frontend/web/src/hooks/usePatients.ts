'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type { Patient, PaginatedResponse, VitalSign, LabResult } from '@/types';

export function usePatients(params?: { search?: string; page?: number; district?: string }) {
  const queryParams = new URLSearchParams();
  if (params?.search) queryParams.set('search', params.search);
  if (params?.page) queryParams.set('page', String(params.page));
  if (params?.district) queryParams.set('district', params.district);

  return useQuery<PaginatedResponse<Patient>>({
    queryKey: ['patients', params],
    queryFn: () => api.get(`/patients?${queryParams.toString()}`),
  });
}

export function usePatient(id: string) {
  return useQuery<Patient>({
    queryKey: ['patient', id],
    queryFn: () => api.get(`/patients/${id}`),
    enabled: !!id,
  });
}

export function usePatientVitals(patientId: string) {
  return useQuery<VitalSign[]>({
    queryKey: ['patient-vitals', patientId],
    queryFn: () => api.get(`/patients/${patientId}/vitals`),
    enabled: !!patientId,
  });
}

export function usePatientLabs(patientId: string) {
  return useQuery<LabResult[]>({
    queryKey: ['patient-labs', patientId],
    queryFn: () => api.get(`/patients/${patientId}/lab-results`),
    enabled: !!patientId,
  });
}

export function useCreatePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Patient>) => api.post('/patients', data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['patients'] }); },
  });
}

export function useRecordVitals() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<VitalSign>) => api.post('/vitals', data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['patient-vitals', variables.patient_id] });
    },
  });
}
