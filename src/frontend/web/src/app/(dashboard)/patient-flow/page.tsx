'use client';

import { useMemo, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  Clock,
  Loader2,
  Plus,
  RefreshCw,
  Users,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { StartJourneyDialog } from '@/components/patient-flow/StartJourneyDialog';
import { RoutePatientDialog } from '@/components/patient-flow/RoutePatientDialog';
import { QueueRow } from '@/components/patient-flow/QueueRow';
import { useFlowDestinations, useFlowQueue, useFlowStats } from '@/hooks/usePatientFlow';
import type { FlowQueueItem, FlowStepStatus, JourneyPriority } from '@/types';

export default function PatientFlowPage() {
  const [servicePoint, setServicePoint] = useState('all');
  const [priority, setPriority] = useState('all');
  const [status, setStatus] = useState('all');
  const [startOpen, setStartOpen] = useState(false);
  const [routeItem, setRouteItem] = useState<FlowQueueItem | null>(null);

  const filters = useMemo(
    () => ({
      service_point: servicePoint === 'all' ? undefined : servicePoint,
      status: status === 'all' ? undefined : (status as FlowStepStatus),
    }),
    [servicePoint, status]
  );

  const queue = useFlowQueue(filters);
  const stats = useFlowStats();
  const { data: destinations } = useFlowDestinations();

  const items = useMemo(() => {
    const rows = queue.data?.items ?? [];
    if (priority === 'all') return rows;
    return rows.filter((item) => item.priority === (priority as JourneyPriority));
  }, [queue.data?.items, priority]);

  const statCards = [
    {
      label: 'Waiting',
      value: stats.data?.waiting ?? 0,
      icon: Users,
      color: 'text-amber-600 bg-amber-100',
    },
    {
      label: 'In progress',
      value: (stats.data?.called ?? 0) + (stats.data?.in_progress ?? 0),
      icon: Activity,
      color: 'text-blue-600 bg-blue-100',
    },
    {
      label: 'Completed today',
      value: stats.data?.completed_today ?? 0,
      icon: CheckCircle2,
      color: 'text-green-600 bg-green-100',
    },
    {
      label: 'Longest wait',
      value: `${stats.data?.longest_wait_minutes ?? 0}m`,
      icon: Clock,
      color: 'text-red-600 bg-red-100',
    },
  ];

  const refresh = () => {
    queue.refetch();
    stats.refetch();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <Activity className="h-6 w-6 text-healthcare-green" />
            Patient Flow
          </h1>
          <p className="text-muted-foreground">
            Live queue, routing and referral tracking across every service point.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={refresh} disabled={queue.isFetching}>
            <RefreshCw className={`mr-2 h-4 w-4 ${queue.isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={() => setStartOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Check in patient
          </Button>
        </div>
      </div>

      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        {statCards.map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardContent className="flex items-center gap-3 p-4">
              <div className={`flex h-10 w-10 items-center justify-center rounded-full ${color}`}>
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xl font-bold">{value}</p>
                <p className="text-xs text-muted-foreground">{label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="text-lg">Live queue</CardTitle>
          <div className="flex flex-wrap gap-2">
            <Select value={servicePoint} onValueChange={setServicePoint}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="All service points" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All service points</SelectItem>
                {(destinations?.service_points ?? []).map((point) => (
                  <SelectItem key={point.code} value={point.code}>
                    {point.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="All priorities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All priorities</SelectItem>
                <SelectItem value="emergency">Emergency</SelectItem>
                <SelectItem value="urgent">Urgent</SelectItem>
                <SelectItem value="routine">Routine</SelectItem>
              </SelectContent>
            </Select>

            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="Active" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Active</SelectItem>
                <SelectItem value="waiting">Waiting</SelectItem>
                <SelectItem value="called">Called</SelectItem>
                <SelectItem value="in_progress">In progress</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {queue.isLoading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : queue.isError ? (
            <div className="py-10 text-center text-sm text-destructive">
              {queue.error instanceof Error ? queue.error.message : 'Unable to load the queue'}
            </div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center">
              <Users className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
              <p className="text-sm font-medium">The queue is clear</p>
              <p className="text-sm text-muted-foreground">
                Check in a patient to start a new journey.
              </p>
              <Button className="mt-4" variant="outline" onClick={() => setStartOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Check in patient
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Patient</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Wait</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <QueueRow
                    key={item.step_id}
                    item={item}
                    onRoute={(selected) => setRouteItem(selected)}
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Queue by service point</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {Object.entries(stats.data?.by_service_point ?? {}).length === 0 ? (
              <p className="text-sm text-muted-foreground">No active patients.</p>
            ) : (
              Object.entries(stats.data?.by_service_point ?? {}).map(([code, count]) => (
                <Badge key={code} variant="outline" className="px-3 py-1">
                  {code.replace(/_/g, ' ')}: {count}
                </Badge>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <StartJourneyDialog open={startOpen} onOpenChange={setStartOpen} />
      {routeItem && (
        <RoutePatientDialog
          journeyId={routeItem.journey_id}
          open={!!routeItem}
          onOpenChange={(open) => !open && setRouteItem(null)}
          currentServicePoint={routeItem.service_point}
          onRouted={() => setRouteItem(null)}
        />
      )}
    </div>
  );
}
