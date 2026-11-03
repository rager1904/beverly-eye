import type { BadgeProps } from '@/components/ui/badge';
import type { FlowStepStatus, JourneyPriority, JourneyStatus } from '@/types';

export function priorityVariant(priority: JourneyPriority): BadgeProps['variant'] {
  if (priority === 'emergency') return 'critical';
  if (priority === 'urgent') return 'warning';
  return 'secondary';
}

export function stepStatusVariant(status: FlowStepStatus): BadgeProps['variant'] {
  if (status === 'waiting') return 'warning';
  if (status === 'called') return 'info';
  if (status === 'in_progress') return 'default';
  if (status === 'completed') return 'success';
  if (status === 'skipped') return 'outline';
  return 'destructive';
}

export function journeyStatusVariant(status: JourneyStatus): BadgeProps['variant'] {
  if (status === 'waiting') return 'warning';
  if (status === 'in_progress') return 'info';
  if (status === 'completed') return 'success';
  return 'destructive';
}

const servicePointLabels: Record<string, string> = {
  registration: 'Registration / Counter',
  triage: 'Triage / Nurse Station',
  general: 'General Clinic',
  eye: 'Eye Clinic',
  dental: 'Dental Clinic',
  consultation: 'Consultation Room',
  laboratory: 'Laboratory',
  pharmacy: 'Pharmacy',
  imaging: 'Imaging / Radiology',
  procedure: 'Procedure Room',
  cashier: 'Cashier / Billing',
  admission: 'Ward / Admission',
  referral: 'Referral Desk',
  discharge: 'Discharge Desk',
  other: 'Other',
};

export function servicePointLabel(code?: string | null): string {
  if (!code) return 'Not set';
  return servicePointLabels[code] ?? code.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatDateTime(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString(undefined, {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatWait(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  return remaining ? `${hours}h ${remaining}m` : `${hours}h`;
}

const paymentSchemeLabels: Record<string, string> = {
  cash: 'Cash',
  nhima: 'NHIMA',
  prudential: 'Prudential',
  sanlam: 'Sanlam',
  madison: 'Madison',
  jubilee: 'Jubilee',
  employer: 'Employer scheme',
  other: 'Other scheme',
};

export function paymentSchemeLabel(scheme?: string | null): string {
  if (!scheme) return 'Cash';
  return paymentSchemeLabels[scheme] ?? scheme.replace(/_/g, ' ');
}

export function visitTypeLabel(visitType?: string | null): string {
  return visitType === 'review' ? 'Review' : 'New visit';
}

export function paymentStatusVariant(status?: string | null): BadgeProps['variant'] {
  return status === 'paid' ? 'success' : 'warning';
}
