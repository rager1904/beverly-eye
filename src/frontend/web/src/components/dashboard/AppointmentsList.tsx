'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Calendar, Clock, Video, MapPin } from 'lucide-react';
import { formatTime } from '@/lib/utils';
import type { Appointment } from '@/types';

interface AppointmentsListProps {
  appointments: Appointment[];
  isLoading?: boolean;
  title?: string;
}

const statusColors: Record<string, string> = {
  scheduled: 'bg-blue-100 text-blue-800',
  confirmed: 'bg-green-100 text-green-800',
  'in-progress': 'bg-purple-100 text-purple-800',
  completed: 'bg-gray-100 text-gray-800',
  cancelled: 'bg-red-100 text-red-800',
  'no-show': 'bg-amber-100 text-amber-800',
};

const typeIcons = {
  'in-person': MapPin,
  telemedicine: Video,
  'home-visit': MapPin,
};

export function AppointmentsList({ appointments, isLoading, title = "Today's Appointments" }: AppointmentsListProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
        <CardContent><div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => (<div key={i} className="h-20 bg-muted animate-pulse rounded-lg" />))}</div></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Calendar className="h-5 w-5 text-healthcare-blue" />
          {title}
        </CardTitle>
        <Badge variant="outline">{appointments.length} total</Badge>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {appointments.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No appointments</p>
          ) : (
            appointments.map((apt) => {
              const TypeIcon = typeIcons[apt.appointment_type] || MapPin;
              return (
                <div key={apt.id} className="flex items-start gap-3 p-3 rounded-lg border hover:bg-accent/50 transition-colors">
                  <div className="flex-shrink-0 w-16 text-center">
                    <div className="text-lg font-bold text-healthcare-blue">{formatTime(apt.start_time)}</div>
                    <Badge variant="outline" className={`text-xs mt-1 ${statusColors[apt.status] || ''}`}>{apt.status}</Badge>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{apt.patient?.name || 'Patient'}</p>
                    <p className="text-sm text-muted-foreground truncate">{apt.reason || 'No reason specified'}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1"><TypeIcon className="h-3 w-3" />{apt.appointment_type.replace('-', ' ')}</span>
                      {apt.notes && <span className="truncate">{apt.notes}</span>}
                    </div>
                  </div>
                  {apt.appointment_type === 'telemedicine' && apt.status === 'confirmed' && (
                    <Badge className="bg-healthcare-green text-white flex-shrink-0">Join</Badge>
                  )}
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
