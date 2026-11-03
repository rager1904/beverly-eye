'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PatientQueue } from '@/components/dashboard/PatientQueue';
import { AppointmentsList } from '@/components/dashboard/AppointmentsList';
import { VitalSigns } from '@/components/dashboard/VitalSigns';
import { SoapNoteEditor } from '@/components/provider/SoapNoteEditor';
import { VoiceRecorder } from '@/components/provider/VoiceRecorder';
import { AiChatWidget } from '@/components/patient/AiChatWidget';
import Link from 'next/link';
import {
  Calendar, Video, FileText, Bell, TrendingUp, Clock, MessageSquare, Plus, Stethoscope, Loader2
} from 'lucide-react';
import type { Appointment, QueueEntry } from '@/types';

interface VitalSign {
  id: string; patient_id: string;
  blood_pressure_systolic: number; blood_pressure_diastolic: number;
  heart_rate: number; respiratory_rate: number; temperature: number; oxygen_saturation: number;
  recorded_at: string; recorded_by: string;
}

interface LabResult {
  id: string; patient_id: string; order_description: string; result_value: string;
  reference_range_low?: string; reference_range_high?: string; interpretation: string;
  status: string; ordered_datetime: string;
}

export default function ProviderDashboard() {
  const [showSoapEditor, setShowSoapEditor] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [vitals, setVitals] = useState<VitalSign | null>(null);
  const [criticalLabs, setCriticalLabs] = useState<LabResult[]>([]);
  const token = useAuthStore((s) => s.accessToken);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [aptRes, labRes] = await Promise.all([
        fetch('/api/v1/appointments?per_page=20', { headers }),
        fetch('/api/v1/emr/orders?status=completed&per_page=10', { headers }),
      ]);
      if (aptRes.ok) {
        const data = await aptRes.json();
        setAppointments(data.items || data || []);
      }
      if (labRes.ok) {
        const data = await labRes.json();
        const items = data.items || data || [];
        setCriticalLabs(items.filter((l: LabResult) => l.interpretation === 'critical'));
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Stethoscope className="h-6 w-6 text-healthcare-blue" />
            Provider Dashboard
          </h1>
          <p className="text-muted-foreground">{new Date().toLocaleDateString('en-ZM', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowSoapEditor(!showSoapEditor)}>
            <FileText className="h-4 w-4 mr-1" />SOAP Note
          </Button>
          <Button asChild className="bg-healthcare-green hover:bg-healthcare-green-dark">
            <Link href="/appointments/new"><Plus className="h-4 w-4 mr-1" />New Appointment</Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Today\'s Patients', value: appointments.length.toString(), icon: Calendar, color: 'text-blue-600 bg-blue-100' },
          { label: 'In Queue', value: queue.length.toString(), icon: Clock, color: 'text-amber-600 bg-amber-100' },
          { label: 'Telemedicine', value: appointments.filter((a) => a.appointment_type === 'telemedicine').length.toString(), icon: Video, color: 'text-purple-600 bg-purple-100' },
          { label: 'Critical Labs', value: criticalLabs.length.toString(), icon: Bell, color: 'text-red-600 bg-red-100' },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardContent className="p-4 flex items-center gap-4">
              <div className={`w-12 h-12 rounded-lg ${color} flex items-center justify-center`}>
                <Icon className="h-6 w-6" />
              </div>
              <div>
                <p className="text-2xl font-bold">{value}</p>
                <p className="text-xs text-muted-foreground">{label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <AppointmentsList appointments={appointments} title="Today's Schedule" />

            {showSoapEditor && (
              <SoapNoteEditor encounterId="enc-1" onSave={(note) => console.log('Saved SOAP:', note)} />
            )}

            <VoiceRecorder onTranscriptionComplete={(text) => console.log('Transcribed:', text)} />
          </div>

          <div className="space-y-6">
            <PatientQueue entries={queue} />

            {vitals && <VitalSigns vitals={vitals} title="Current Patient Vitals" />}

            <Card>
              <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Bell className="h-5 w-5 text-red-500" />Critical Lab Results</CardTitle></CardHeader>
              <CardContent>
                {criticalLabs.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">No critical lab results</p>
                ) : (
                  <div className="space-y-3">
                    {criticalLabs.map((lab) => (
                      <div key={lab.id} className="p-3 rounded-lg border border-red-200 bg-red-50">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-sm">{lab.order_description || 'Lab Result'}</span>
                          <Badge variant="critical">Critical</Badge>
                        </div>
                        <p className="text-sm mt-1">
                          Result: <span className="font-bold text-red-600">{lab.result_value}</span>
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">{lab.ordered_datetime}</p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
      <AiChatWidget open={chatOpen} onOpenChange={setChatOpen} />
    </div>
  );
}
