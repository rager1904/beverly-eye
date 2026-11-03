'use client';

import Link from 'next/link';
import { ArrowRight, BellRing, CheckCircle2, Loader2, Play } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TableCell, TableRow } from '@/components/ui/table';
import {
  useCallStep,
  useCompleteStep,
  useStartStep,
} from '@/hooks/usePatientFlow';
import type { FlowQueueItem } from '@/types';
import {
  formatWait,
  paymentSchemeLabel,
  paymentStatusVariant,
  priorityVariant,
  servicePointLabel,
  stepStatusVariant,
  visitTypeLabel,
} from './flow-utils';

interface QueueRowProps {
  item: FlowQueueItem;
  onRoute: (item: FlowQueueItem) => void;
}

export function QueueRow({ item, onRoute }: QueueRowProps) {
  const callStep = useCallStep(item.journey_id);
  const startStep = useStartStep(item.journey_id);
  const completeStep = useCompleteStep(item.journey_id);

  const busy = callStep.isPending || startStep.isPending || completeStep.isPending;

  const run = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action();
      toast.success(message);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Action failed');
    }
  };

  return (
    <TableRow>
      <TableCell className="font-medium">#{item.position}</TableCell>
      <TableCell>
        <div>
          <Link href={`/patient-flow/${item.journey_id}`} className="font-medium hover:underline">
            {item.patient_name}
          </Link>
          <p className="text-xs text-muted-foreground">
            {item.nrc_number || item.phone || 'No identifier'} · {item.journey_number}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <Badge variant="outline">{visitTypeLabel(item.visit_type)}</Badge>
            <Badge variant="outline">{paymentSchemeLabel(item.payment_scheme)}</Badge>
            <Badge variant={paymentStatusVariant(item.payment_status)}>
              {item.payment_status}
            </Badge>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant={priorityVariant(item.priority)}>{item.priority}</Badge>
      </TableCell>
      <TableCell>
        <div>
          <p className="text-sm">{servicePointLabel(item.service_point)}</p>
          <p className="text-xs text-muted-foreground">
            {item.department_name || item.provider_name || 'Unassigned'}
          </p>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant={stepStatusVariant(item.status)}>{item.status.replace(/_/g, ' ')}</Badge>
      </TableCell>
      <TableCell className="whitespace-nowrap">{formatWait(item.wait_minutes)}</TableCell>
      <TableCell>
        <div className="flex flex-wrap items-center gap-1.5">
          {item.status === 'waiting' && (
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={() => run(() => callStep.mutateAsync(item.step_id), 'Patient called')}
            >
              {callStep.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <BellRing className="mr-1 h-3.5 w-3.5" />}
              Call
            </Button>
          )}
          {(item.status === 'waiting' || item.status === 'called') && (
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={() => run(() => startStep.mutateAsync(item.step_id), 'Consultation started')}
            >
              {startStep.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <Play className="mr-1 h-3.5 w-3.5" />}
              Start
            </Button>
          )}
          {item.status !== 'completed' && item.status !== 'skipped' && item.status !== 'cancelled' && (
            <>
              <Button
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() =>
                  run(
                    () => completeStep.mutateAsync({ stepId: item.step_id, input: { outcome: 'completed' } }),
                    'Step completed'
                  )
                }
              >
                {completeStep.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="mr-1 h-3.5 w-3.5" />}
                Complete
              </Button>
              <Button size="sm" disabled={busy} onClick={() => onRoute(item)}>
                <ArrowRight className="mr-1 h-3.5 w-3.5" />
                Send
              </Button>
            </>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}
