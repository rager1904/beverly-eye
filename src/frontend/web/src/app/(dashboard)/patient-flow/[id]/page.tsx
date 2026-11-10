'use client';

import { Suspense, useState } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import {
  ArrowLeft,
  ArrowRight,
  BellRing,
  CheckCircle2,
  Loader2,
  LogOut,
  Play,
  Send,
  Stethoscope,
  User,
} from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { JourneyTimeline } from '@/components/patient-flow/JourneyTimeline';
import { RoutePatientDialog } from '@/components/patient-flow/RoutePatientDialog';
import { CloseJourneyDialog } from '@/components/patient-flow/CloseJourneyDialog';
import {
  useCallStep,
  useCompleteStep,
  useJourney,
  useSkipStep,
  useStartStep,
} from '@/hooks/usePatientFlow';
import {
  formatDateTime,
  formatWait,
  journeyStatusVariant,
  paymentSchemeLabel,
  paymentStatusVariant,
  priorityVariant,
  servicePointLabel,
  stepStatusVariant,
  visitTypeLabel,
} from '@/components/patient-flow/flow-utils';
import type { JourneyStep } from '@/types';

function minutesSince(value?: string | null): number {
  if (!value) return 0;
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return 0;
  return Math.max(0, Math.floor((Date.now() - then) / 60000));
}

export default function JourneyDetailPage() {
  return <Suspense fallback={null}><JourneyDetail /></Suspense>;
}

function JourneyDetail() {
  const facilityId = useSearchParams().get('facility_id') ?? undefined;
  const params = useParams();
  const rawId = params?.id;
  const journeyId = Array.isArray(rawId) ? rawId[0] ?? '' : rawId ?? '';

  const [routeOpen, setRouteOpen] = useState(false);
  const [closeOpen, setCloseOpen] = useState(false);

  const journey = useJourney(journeyId, facilityId, routeOpen || closeOpen);
  const callStep = useCallStep(journeyId, facilityId);
  const startStep = useStartStep(journeyId, facilityId);
  const completeStep = useCompleteStep(journeyId, facilityId);
  const skipStep = useSkipStep(journeyId, facilityId);

  if (journey.isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (journey.isError || !journey.data) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/patient-flow">
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to queue
          </Link>
        </Button>
        <Card>
          <CardContent className="py-12 text-center text-sm text-destructive">
            {journey.error instanceof Error ? journey.error.message : 'Journey not found'}
          </CardContent>
        </Card>
      </div>
    );
  }

  const data = journey.data;
  const steps = [...data.steps].sort((a, b) => a.step_number - b.step_number);
  const activeStep: JourneyStep | undefined =
    steps.find((step) => step.id === data.current_step_id) ??
    steps.find((step) => ['waiting', 'called', 'in_progress'].includes(step.status));

  const isClosed = data.status === 'completed' || data.status === 'cancelled';
  const busy = callStep.isPending || startStep.isPending || completeStep.isPending || skipStep.isPending;

  const run = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      toast.success(message);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Action failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/patient-flow">
              <ArrowLeft className="mr-1 h-4 w-4" />
              Back to queue
            </Link>
          </Button>
          <h1 className="mt-2 flex flex-wrap items-center gap-2 text-2xl font-bold">
            {data.patient ? `${data.patient.first_name} ${data.patient.last_name}` : 'Patient journey'}
            <Badge variant={journeyStatusVariant(data.status)}>
              {data.status.replace(/_/g, ' ')}
            </Badge>
            <Badge variant={priorityVariant(data.priority)}>{data.priority}</Badge>
          </h1>
          <p className="text-muted-foreground">
            {data.journey_number} · Checked in {formatDateTime(data.checked_in_at)}
          </p>
        </div>
        {!isClosed && (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setCloseOpen(true)}>
              <LogOut className="mr-2 h-4 w-4" />
              Close journey
            </Button>
            <Button onClick={() => setRouteOpen(true)}>
              <Send className="mr-2 h-4 w-4" />
              Send patient onward
            </Button>
          </div>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Current location</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-lg font-semibold">
                  {servicePointLabel(data.current_service_point)}
                </p>
                <p className="text-sm text-muted-foreground">
                  {data.current_department_name || 'No department assigned'}
                  {data.current_provider_name ? ` · ${data.current_provider_name}` : ''}
                </p>
              </div>
              {activeStep ? (
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={stepStatusVariant(activeStep.status)}>
                    {activeStep.status.replace(/_/g, ' ')}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    Waiting {formatWait(minutesSince(activeStep.created_at))}
                  </span>
                </div>
              ) : (
                <Badge variant="outline">{isClosed ? 'Visit closed' : 'No active step'}</Badge>
              )}
            </div>

            {activeStep && !isClosed && (
              <div className="flex flex-wrap gap-2 border-t pt-4">
                {activeStep.status === 'waiting' && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    onClick={() => run(() => callStep.mutateAsync(activeStep.id), 'Patient called')}
                  >
                    {callStep.isPending ? (
                      <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                    ) : (
                      <BellRing className="mr-1 h-4 w-4" />
                    )}
                    Call
                  </Button>
                )}
                {(activeStep.status === 'waiting' || activeStep.status === 'called') && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    onClick={() => run(() => startStep.mutateAsync(activeStep.id), 'Step started')}
                  >
                    {startStep.isPending ? (
                      <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-1 h-4 w-4" />
                    )}
                    Start
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busy}
                  onClick={() =>
                    run(
                      () =>
                        completeStep.mutateAsync({
                          stepId: activeStep.id,
                          input: { outcome: 'completed' },
                        }),
                      'Step completed'
                    )
                  }
                >
                  {completeStep.isPending ? (
                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="mr-1 h-4 w-4" />
                  )}
                  Complete step
                </Button>
                <Button size="sm" disabled={busy} onClick={() => setRouteOpen(true)}>
                  <ArrowRight className="mr-1 h-4 w-4" />
                  Send onward
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy}
                  onClick={() =>
                    run(
                      () =>
                        skipStep.mutateAsync({
                          stepId: activeStep.id,
                          reason: 'Skipped at the service point',
                        }),
                      'Step skipped'
                    )
                  }
                >
                  Skip
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <User className="h-4 w-4" />
              Patient
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="font-medium">
              {data.patient ? `${data.patient.first_name} ${data.patient.last_name}` : 'Unknown patient'}
            </p>
            <Button variant="link" size="sm" className="h-auto p-0" asChild>
              <Link href={`/patient/${data.patient_id}`}>Open patient record</Link>
            </Button>
            <p className="text-muted-foreground">
              {data.patient?.nrc_number || 'No NRC'} · {data.patient?.phone || 'No phone'}
            </p>
            <div className="space-y-2 border-t pt-3">
              <p className="text-xs uppercase text-muted-foreground">Visit &amp; billing</p>
              <div className="flex flex-wrap gap-1.5">
                <Badge variant="outline">{visitTypeLabel(data.visit_type)}</Badge>
                <Badge variant="outline">{paymentSchemeLabel(data.payment_scheme)}</Badge>
                <Badge variant={paymentStatusVariant(data.payment_status)}>
                  {data.payment_status}
                </Badge>
              </div>
              {data.scheme_number && (
                <p className="text-muted-foreground">
                  Scheme number: {data.scheme_number}
                </p>
              )}
            </div>
            {data.chief_complaint && (
              <div className="pt-2">
                <p className="text-xs uppercase text-muted-foreground">Chief complaint</p>
                <p>{data.chief_complaint}</p>
              </div>
            )}
            {data.arrival_notes && (
              <div className="pt-2">
                <p className="text-xs uppercase text-muted-foreground">Arrival notes</p>
                <p className="text-muted-foreground">{data.arrival_notes}</p>
              </div>
            )}
            <div className="flex items-center gap-2 pt-2 text-xs text-muted-foreground">
              <Stethoscope className="h-3.5 w-3.5" />
              Journey opened {formatDateTime(data.created_at)}
            </div>
            {data.closed_reason && (
              <div className="pt-2">
                <p className="text-xs uppercase text-muted-foreground">Closed</p>
                <p className="text-muted-foreground">{data.closed_reason}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Journey timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <JourneyTimeline journey={data} />
        </CardContent>
      </Card>

      {!isClosed && (
        <>
          <RoutePatientDialog
            journeyId={journeyId}
            facilityId={facilityId}
            open={routeOpen}
            onOpenChange={setRouteOpen}
            currentServicePoint={data.current_service_point}
            onRouted={() => setRouteOpen(false)}
          />
          <CloseJourneyDialog
            journeyId={journeyId}
            facilityId={facilityId}
            open={closeOpen}
            onOpenChange={setCloseOpen}
          />
        </>
      )}
    </div>
  );
}
