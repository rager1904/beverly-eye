'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Pill, CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import type { Medication } from '@/types';
import { formatDate } from '@/lib/utils';

interface MedicationReminderProps {
  medications: Medication[];
  isLoading?: boolean;
}

export function MedicationReminder({ medications, isLoading }: MedicationReminderProps) {
  const activeMeds = medications.filter((m) => m.status === 'active');
  const today = new Date().toISOString().split('T')[0];

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Pill className="h-5 w-5" />Medications</CardTitle></CardHeader>
        <CardContent><div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => (<div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />))}</div></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Pill className="h-5 w-5 text-healthcare-blue" />
          Medication Reminders
        </CardTitle>
        <Badge variant="outline">{activeMeds.length} active</Badge>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {activeMeds.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No active medications</p>
          ) : (
            activeMeds.map((med) => {
              const hasRefill = med.refill_remaining !== undefined && med.refill_remaining <= 3;
              return (
                <div key={med.id} className="flex items-start gap-3 p-3 rounded-lg border hover:bg-accent/50 transition-colors">
                  <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${hasRefill ? 'bg-red-100' : 'bg-green-100'}`}>
                    {hasRefill ? <AlertTriangle className="h-5 w-5 text-red-500" /> : <CheckCircle className="h-5 w-5 text-green-500" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{med.name}</span>
                      <Badge variant={hasRefill ? 'warning' : 'success'} className="text-xs">{med.dosage}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{med.frequency} - {med.route}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1"><Clock className="h-3 w-3" />Started {formatDate(med.start_date)}</span>
                      {hasRefill && <span className="text-red-500 font-medium">{med.refill_remaining} refills left</span>}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
