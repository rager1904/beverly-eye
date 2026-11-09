'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Calendar, Search, Plus, ChevronRight, MapPin, Clock, User, Video, Filter, Loader2 } from 'lucide-react';
import { AiChatWidget } from '@/components/patient/AiChatWidget';
import Link from 'next/link';

interface Appointment {
  id: string;
  patient_name?: string;
  appointment_type?: string;
  provider_name?: string;
  location?: string;
  start_time: string;
  status: string;
  mode?: string;
}

export default function AppointmentsPage() {
  const [chatOpen, setChatOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((s) => s.accessToken);

  const fetchAppointments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/appointments?per_page=50', {
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
  }, [token]);

  useEffect(() => { fetchAppointments(); }, [fetchAppointments]);

  const filtered = appointments.filter((a) =>
    (a.patient_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (a.appointment_type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (a.provider_name || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const upcoming = filtered.filter((a) => a.status === 'scheduled' || a.status === 'confirmed');
  const completed = filtered.filter((a) => a.status === 'completed');

  const renderAppointmentRow = (apt: Appointment) => (
    <div key={apt.id} className="flex items-start gap-4 p-4 rounded-lg border hover:bg-accent/50 transition-colors">
      <div className="w-16 text-center">
        <div className="text-xl font-bold text-healthcare-green">{new Date(apt.start_time).getDate()}</div>
        <div className="text-xs text-muted-foreground">{new Date(apt.start_time).toLocaleDateString('en-ZM', { month: 'short', year: '2-digit' })}</div>
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium">{apt.appointment_type || 'Appointment'}</span>
          <Badge variant={apt.status === 'confirmed' ? 'success' : 'outline'}>{apt.status}</Badge>
          <Badge variant={apt.mode === 'telemedicine' || apt.appointment_type === 'telemedicine' ? 'warning' : 'secondary'}>{apt.mode || apt.appointment_type || 'in-person'}</Badge>
        </div>
        <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1"><User className="h-3 w-3" />{apt.patient_name || 'N/A'}</span>
          <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{new Date(apt.start_time).toLocaleTimeString('en-ZM', { hour: '2-digit', minute: '2-digit' })}</span>
          {apt.location && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{apt.location}</span>}
        </div>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" size="sm">Reschedule</Button>
        {(apt.mode === 'telemedicine' || apt.appointment_type === 'telemedicine') && (
          <Button asChild size="sm" className="bg-healthcare-green hover:bg-healthcare-green-dark">
            <Link href="/telemedicine"><Video className="h-3 w-3 mr-1" />Join</Link>
          </Button>
        )}
      </div>
    </div>
  );

  const renderCompactRow = (apt: Appointment) => (
    <div key={apt.id} className="flex items-center justify-between p-4 rounded-lg border">
      <div>
        <div className="flex items-center gap-2">
          <span className="font-medium">{apt.appointment_type || 'Appointment'}</span>
          <Badge variant={apt.status === 'confirmed' ? 'success' : apt.status === 'completed' ? 'secondary' : apt.status === 'cancelled' ? 'critical' : 'outline'}>{apt.status}</Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-1">{apt.patient_name || 'N/A'} - {apt.provider_name || 'N/A'} - {new Date(apt.start_time).toLocaleDateString('en-ZM')}</p>
      </div>
      <Button variant="ghost" size="sm">View <ChevronRight className="h-4 w-4 ml-1" /></Button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Calendar className="h-6 w-6 text-healthcare-blue" />
            Appointments
          </h1>
          <p className="text-muted-foreground">Manage your appointments and schedule</p>
        </div>
        <Button asChild className="bg-healthcare-green hover:bg-healthcare-green-dark">
          <Link href="/appointments/new"><Plus className="h-4 w-4 mr-1" />New Appointment</Link>
        </Button>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          <Input placeholder="Search by patient, type, or provider..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-10 h-12 text-base" />
        </div>
        <Button variant="outline"><Filter className="h-4 w-4 mr-1" />Filter</Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <Tabs defaultValue="upcoming">
          <TabsList>
            <TabsTrigger value="upcoming">Upcoming ({upcoming.length})</TabsTrigger>
            <TabsTrigger value="completed">Completed ({completed.length})</TabsTrigger>
            <TabsTrigger value="all">All ({filtered.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="upcoming">
            <Card>
              <CardContent className="p-4">
                {upcoming.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">No upcoming appointments</p>
                ) : (
                  <div className="space-y-3">{upcoming.map(renderAppointmentRow)}</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="completed">
            <Card>
              <CardContent className="p-4">
                {completed.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">No completed appointments</p>
                ) : (
                  <div className="space-y-3">{completed.map(renderCompactRow)}</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="all">
            <Card>
              <CardContent className="p-4">
                <div className="space-y-3">{filtered.map(renderCompactRow)}</div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
      <AiChatWidget open={chatOpen} onOpenChange={setChatOpen} />
    </div>
  );
}
