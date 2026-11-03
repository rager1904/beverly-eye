'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Clock, Users, AlertTriangle } from 'lucide-react';
import type { QueueEntry } from '@/types';

interface PatientQueueProps {
  entries: QueueEntry[];
  isLoading?: boolean;
}

const priorityStyles = {
  emergency: 'bg-red-100 text-red-800 border-red-200',
  urgent: 'bg-amber-100 text-amber-800 border-amber-200',
  normal: 'bg-green-100 text-green-800 border-green-200',
};

const statusStyles = {
  waiting: 'bg-yellow-100 text-yellow-800',
  triage: 'bg-blue-100 text-blue-800',
  'with-provider': 'bg-purple-100 text-purple-800',
  completed: 'bg-green-100 text-green-800',
};

export function PatientQueue({ entries, isLoading }: PatientQueueProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Users className="h-5 w-5" />Patient Queue</CardTitle></CardHeader>
        <CardContent><div className="space-y-3">{Array.from({ length: 4 }).map((_, i) => (<div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />))}</div></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Users className="h-5 w-5 text-healthcare-blue" />
          Patient Queue
        </CardTitle>
        <Badge variant="outline" className="text-sm">{entries.length} waiting</Badge>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {entries.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No patients in queue</p>
          ) : (
            entries.map((entry) => (
              <div key={entry.id} className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{entry.patient_name}</span>
                    <Badge variant="outline" className={`text-xs ${priorityStyles[entry.priority]}`}>{entry.priority}</Badge>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                    <span className={statusStyles[entry.status]?.split(' ')[0] ? `inline-flex items-center px-1.5 py-0.5 rounded text-xs ${statusStyles[entry.status]}` : ''}>
                      {entry.status.replace('-', ' ')}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {entry.estimated_wait_minutes} min wait
                    </span>
                    <span>{entry.department}</span>
                  </div>
                </div>
                {entry.priority === 'emergency' && <AlertTriangle className="h-5 w-5 text-red-500 ml-2 flex-shrink-0" />}
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
