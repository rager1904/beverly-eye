'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type {
  HospitalDepartment,
  HospitalStaff,
  HospitalStaffRole,
} from '@/types';

export interface DepartmentInput {
  name: string;
  code?: string;
  head_of_department?: string;
  location?: string;
  phone_extension?: string;
  is_active?: boolean;
}

export interface StaffInput {
  user_id?: string;
  first_name: string;
  last_name: string;
  role: HospitalStaffRole;
  speciality?: string;
  department_id?: string | null;
  phone?: string;
  email?: string;
  license_number?: string;
  is_active?: boolean;
  max_hours_per_week?: number;
}

export interface StaffListResponse {
  items: HospitalStaff[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export const directoryKeys = {
  all: ['hospital-directory'] as const,
  departments: (includeInactive: boolean) =>
    ['hospital-directory', 'departments', includeInactive] as const,
  staff: ['hospital-directory', 'staff'] as const,
};

function invalidateDirectory(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: directoryKeys.all });
  // Routing selects read from the patient-flow destinations endpoint.
  queryClient.invalidateQueries({ queryKey: ['patient-flow', 'destinations'] });
}

export function useDepartments(includeInactive = true) {
  return useQuery<HospitalDepartment[]>({
    queryKey: directoryKeys.departments(includeInactive),
    queryFn: () =>
      api.get<HospitalDepartment[]>(
        `/hospital/departments${includeInactive ? '?include_inactive=true' : ''}`
      ),
  });
}

export function useStaffDirectory() {
  return useQuery<StaffListResponse>({
    queryKey: directoryKeys.staff,
    queryFn: () => api.get<StaffListResponse>('/hospital/staff?per_page=100'),
  });
}

export function useCreateDepartment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: DepartmentInput) =>
      api.post<HospitalDepartment>('/hospital/departments', input),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}

export function useUpdateDepartment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<DepartmentInput> }) =>
      api.patch<HospitalDepartment>(`/hospital/departments/${id}`, input),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}

export function useDeactivateDepartment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<HospitalDepartment>(`/hospital/departments/${id}`),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}

export function useCreateStaff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: StaffInput) => api.post<HospitalStaff>('/hospital/staff', input),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}

export function useUpdateStaff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<StaffInput> }) =>
      api.patch<HospitalStaff>(`/hospital/staff/${id}`, input),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}

export function useDeactivateStaff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<HospitalStaff>(`/hospital/staff/${id}`),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}
