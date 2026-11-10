'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { withFacility } from '@/lib/facility-scope';
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
  user_id?: string | null;
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

export function useDepartments(includeInactive = true, facilityId?: string) {
  return useQuery<HospitalDepartment[]>({
    queryKey: [...directoryKeys.departments(includeInactive), facilityId],
    queryFn: () =>
      api.get<HospitalDepartment[]>(
        withFacility(`/hospital/departments${includeInactive ? '?include_inactive=true' : ''}`, facilityId)
      ),
  });
}

export function useStaffDirectory(facilityId?: string) {
  return useQuery<StaffListResponse>({
    queryKey: [...directoryKeys.staff, facilityId],
    queryFn: () => api.get<StaffListResponse>(withFacility('/hospital/staff?per_page=100', facilityId)),
  });
}

export function useCreateDepartment(facilityId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: DepartmentInput) =>
      api.post<HospitalDepartment>(withFacility('/hospital/departments', facilityId), input),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}

export function useUpdateDepartment(facilityId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<DepartmentInput> }) =>
      api.patch<HospitalDepartment>(withFacility(`/hospital/departments/${id}`, facilityId), input),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}

export function useDeactivateDepartment(facilityId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<HospitalDepartment>(withFacility(`/hospital/departments/${id}`, facilityId)),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}

export function useCreateStaff(facilityId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: StaffInput) => api.post<HospitalStaff>(withFacility('/hospital/staff', facilityId), input),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}

export function useUpdateStaff(facilityId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<StaffInput> }) =>
      api.patch<HospitalStaff>(withFacility(`/hospital/staff/${id}`, facilityId), input),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}

export function useDeactivateStaff(facilityId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<HospitalStaff>(withFacility(`/hospital/staff/${id}`, facilityId)),
    onSuccess: () => invalidateDirectory(queryClient),
  });
}
