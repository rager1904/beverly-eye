'use client';

import {
  Activity,
  BedDouble,
  Circle,
  ClipboardList,
  CreditCard,
  FlaskConical,
  LogOut,
  Pill,
  Scan,
  Scissors,
  Send,
  Stethoscope,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { FlowStepType, JourneyStep, PatientJourney } from '@/types';
import { formatDateTime, servicePointLabel, stepStatusVariant } from './flow-utils';

const stepIcons: Record<FlowStepType, typeof Circle> = {
  registration: ClipboardList,
  triage: Activity,
  consultation: Stethoscope,
  laboratory: FlaskConical,
  pharmacy: Pill,
  imaging: Scan,
  procedure: Scissors,
  admission: BedDouble,
  cashier: CreditCard,
  referral: Send,
  discharge: LogOut,
  other: Circle,
};

interface JourneyTimelineProps {
  journey: PatientJourney;
}

export function JourneyTimeline({ journey }: JourneyTimelineProps) {
  const steps = [...journey.steps].sort((a, b) => a.step_number - b.step_number);

  if (!steps.length) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          No journey steps recorded yet.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="relative space-y-0">
      <div className="absolute bottom-4 left-5 top-4 w-px bg-border" aria-hidden />
      {steps.map((step) => (
        <TimelineStep key={step.id} step={step} />
      ))}
    </div>
  );
}

function TimelineStep({ step }: { step: JourneyStep }) {
  const Icon = stepIcons[step.step_type] ?? Circle;

  return (
    <div className="relative flex gap-4 pb-5">
      <div className="relative z-10 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border bg-background">
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <Card className="flex-1">
        <CardContent className="space-y-2 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold">
                {step.step_number}. {servicePointLabel(step.service_point)}
              </p>
              <p className="text-xs capitalize text-muted-foreground">
                {step.step_type.replace(/_/g, ' ')}
                {step.department_name ? ` · ${step.department_name}` : ''}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={stepStatusVariant(step.status)}>{step.status.replace(/_/g, ' ')}</Badge>
              {step.outcome && <Badge variant="outline">{step.outcome.replace(/_/g, ' ')}</Badge>}
            </div>
          </div>

          {step.provider_name && (
            <p className="text-sm text-muted-foreground">Clinician: {step.provider_name}</p>
          )}

          {step.reason && <p className="text-sm">{step.reason}</p>}
          {step.notes && <p className="text-sm text-muted-foreground">{step.notes}</p>}

          <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
            <span>Queued: {formatDateTime(step.created_at)}</span>
            {step.called_at && <span>Called: {formatDateTime(step.called_at)}</span>}
            {step.started_at && <span>Started: {formatDateTime(step.started_at)}</span>}
            {step.completed_at && <span>Completed: {formatDateTime(step.completed_at)}</span>}
          </div>

          {step.referred_to_service_point && (
            <p className="text-xs text-muted-foreground">
              Referred to {servicePointLabel(step.referred_to_service_point)}
              {step.referred_to_provider_id ? ' (clinician assigned)' : ''}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
