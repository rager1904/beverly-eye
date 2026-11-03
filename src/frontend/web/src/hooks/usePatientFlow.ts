'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { clinicalApi } from '@/lib/clinical-api';
import type {
  FlowDestinations,
  FlowQueueResponse,
  FlowStats,
  FlowStepOutcome,
  FlowStepStatus,
  FlowStepType,
  JourneyPriority,
  PatientJourney,
  PatientSearchResult,
  PaymentScheme,
  VisitPaymentStatus,
  VisitType,
} from '@/types';

export interface FlowQueueFilters {
  service_point?: string;
  department_id?: string;
  provider_id?: string;
  step_type?: FlowStepType;
  status?: FlowStepStatus;
  include_completed?: boolean;
}

export interface StartJourneyInput {
  patient_id: string;
  encounter_id?: string;
  priority?: JourneyPriority;
  payment_scheme?: PaymentScheme;
  visit_type?: VisitType;
  payment_status?: VisitPaymentStatus;
  scheme_number?: string;
  chief_complaint?: string;
  arrival_notes?: string;
  step_type?: FlowStepType;
  service_point?: string;
  department_id?: string;
  department_name?: string;
  provider_id?: string;
  provider_name?: string;
  reason?: string;
}

export interface RoutePatientInput {
  step_type: FlowStepType;
  service_point: string;
  department_id?: string;
  department_name?: string;
  provider_id?: string;
  provider_name?: string;
  priority?: JourneyPriority;
  reason?: string;
  notes?: string;
  outcome?: FlowStepOutcome;
}

export interface CompleteStepInput {
  outcome?: FlowStepOutcome;
  notes?: string;
}

export interface CloseJourneyInput {
  reason?: string;
  outcome?: FlowStepOutcome;
}

export const flowKeys = {
  all: ['patient-flow'] as const,
  queue: (filters: FlowQueueFilters) => ['patient-flow', 'queue', filters] as const,
  stats: () => ['patient-flow', 'stats'] as const,
  destinations: () => ['patient-flow', 'destinations'] as const,
  journey: (id: string) => ['patient-flow', 'journey', id] as const,
  patientJourneys: (patientId: string) => ['patient-flow', 'patient', patientId] as const,
};

function post<T>(path: string, body?: unknown): Promise<T> {
  return clinicalApi<T>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function invalidateFlow(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: flowKeys.all });
}

export function useFlowQueue(filters: FlowQueueFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value));
  });
  const query = params.toString();

  return useQuery<FlowQueueResponse>({
    queryKey: flowKeys.queue(filters),
    queryFn: () => clinicalApi<FlowQueueResponse>(`patient-flow/queue${query ? `?${query}` : ''}`),
    refetchInterval: 15000,
  });
}

export function useFlowStats() {
  return useQuery<FlowStats>({
    queryKey: flowKeys.stats(),
    queryFn: () => clinicalApi<FlowStats>('patient-flow/stats'),
    refetchInterval: 15000,
  });
}

export function useFlowDestinations() {
  return useQuery<FlowDestinations>({
    queryKey: flowKeys.destinations(),
    queryFn: () => clinicalApi<FlowDestinations>('patient-flow/destinations'),
    staleTime: 60000,
  });
}

export function useJourney(journeyId: string) {
  return useQuery<PatientJourney>({
    queryKey: flowKeys.journey(journeyId),
    queryFn: () => clinicalApi<PatientJourney>(`patient-flow/journeys/${journeyId}`),
    enabled: !!journeyId,
    refetchInterval: 15000,
  });
}

export function usePatientJourneys(patientId: string) {
  return useQuery<PatientJourney[]>({
    queryKey: flowKeys.patientJourneys(patientId),
    queryFn: () => clinicalApi<PatientJourney[]>(`patient-flow/patients/${patientId}/journeys`),
    enabled: !!patientId,
  });
}

export function usePatientSearch(query: string) {
  return useQuery<{ items: PatientSearchResult[]; total: number }>({
    queryKey: ['patient-search', query],
    queryFn: () =>
      clinicalApi<{ items: PatientSearchResult[]; total: number }>(
        `emr/patients?query=${encodeURIComponent(query)}&per_page=10`
      ),
    enabled: query.trim().length >= 2,
  });
}

export function useStartJourney() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: StartJourneyInput) => post<PatientJourney>('patient-flow/journeys', input),
    onSuccess: () => invalidateFlow(queryClient),
  });
}

export function useRoutePatient(journeyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: RoutePatientInput) =>
      post<PatientJourney>(`patient-flow/journeys/${journeyId}/route`, input),
    onSuccess: () => invalidateFlow(queryClient),
  });
}

export function useCallStep(journeyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (stepId: string) =>
      post<PatientJourney>(`patient-flow/journeys/${journeyId}/steps/${stepId}/call`),
    onSuccess: () => invalidateFlow(queryClient),
  });
}

export function useStartStep(journeyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (stepId: string) =>
      post<PatientJourney>(`patient-flow/journeys/${journeyId}/steps/${stepId}/start`),
    onSuccess: () => invalidateFlow(queryClient),
  });
}

export function useCompleteStep(journeyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ stepId, input }: { stepId: string; input: CompleteStepInput }) =>
      post<PatientJourney>(`patient-flow/journeys/${journeyId}/steps/${stepId}/complete`, input),
    onSuccess: () => invalidateFlow(queryClient),
  });
}

export function useSkipStep(journeyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      stepId,
      reason,
      outcome,
    }: {
      stepId: string;
      reason?: string;
      outcome?: FlowStepOutcome;
    }) =>
      post<PatientJourney>(`patient-flow/journeys/${journeyId}/steps/${stepId}/skip`, {
        reason,
        outcome: outcome ?? 'cancelled',
      }),
    onSuccess: () => invalidateFlow(queryClient),
  });
}

export function useCloseJourney(journeyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CloseJourneyInput) =>
      post<PatientJourney>(`patient-flow/journeys/${journeyId}/close`, input),
    onSuccess: () => invalidateFlow(queryClient),
  });
}
