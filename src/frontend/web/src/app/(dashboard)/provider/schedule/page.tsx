'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar as CalendarIcon, ArrowLeft, Clock, Users, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import Link from 'next/link';

const hours = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00'];

interface Appointment {
  id: string;
  start_time: string;
  patient_name?: string;
  appointment_type?: string;
  status: string;
}

export default function ProviderSchedulePage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((s) => s.accessToken);

  const fetchAppointments = useCallback(async () => {
    setLoading(true);
    try {
      const dateStr = currentDate.toISOString().split('T')[0];
      const res = await fetch(`/api/v1/appointments?date=${dateStr}&per_page=50`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAppointments(data.items || data || []);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [token, currentDate]);

  useEffect(() => { fetchAppointments(); }, [fetchAppointments]);

  const todayStr = currentDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

  const prevDay = () => setCurrentDate(new Date(currentDate.getTime() - 86400000));
  const nextDay = () => setCurrentDate(new Date(currentDate.getTime() + 86400000));

  const getAppointmentsForHour = (hour: string) => {
    return appointments.filter((a) => {
      const aptHour = new Date(a.start_time).getHours().toString().padStart(2, '0') + ':00';
      return aptHour === hour;
    });
  };

  const statusColor = (s: string) => {
    switch (s) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'in-progress': return 'bg-blue-100 text-blue-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800';
      case 'scheduled': return 'bg-gray-100 text-gray-800';
      case 'confirmed': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild><Link href="/provider"><ArrowLeft className="h-4 w-4 mr-1" />Back</Link></Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <CalendarIcon className="h-6 w-6 text-healthcare-blue" />Schedule
          </h1>
          <p className="text-muted-foreground">Your daily appointment schedule</p>
        </div>
        <Button variant="outline" asChild><Link href="/appointments/new">New Appointment</Link></Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-4">
            <Button variant="ghost" size="icon" onClick={prevDay}><ChevronLeft className="h-5 w-5" /></Button>
            <div className="text-center">
              <p className="font-medium">{todayStr}</p>
              {!loading && <p className="text-xs text-muted-foreground">{appointments.length} appointments</p>}
            </div>
            <Button variant="ghost" size="icon" onClick={nextDay}><ChevronRight className="h-5 w-5" /></Button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : (
            <div className="space-y-1">
              {hours.map((hour) => {
                const slots = getAppointmentsForHour(hour);
                return (
                  <div key={hour} className="flex gap-4 p-2 rounded-lg hover:bg-accent/50">
                    <div className="w-16 text-sm text-muted-foreground pt-1">{hour}</div>
                    <div className="flex-1 space-y-1">
                      {slots.length === 0 ? (
                        <p className="text-xs text-muted-foreground italic">Available</p>
                      ) : (
                        slots.map((appt) => (
                          <div key={appt.id} className="p-2 rounded-md border bg-card flex items-center justify-between">
                            <div>
                              <p className="text-sm font-medium">{appt.patient_name || 'Patient'}</p>
                              <p className="text-xs text-muted-foreground">{appt.appointment_type || 'Appointment'}</p>
                            </div>
                            <Badge variant="outline" className={statusColor(appt.status)}>{appt.status}</Badge>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
