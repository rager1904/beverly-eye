'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MedicationReminder } from '@/components/patient/MedicationReminder';
import { HealthEducation } from '@/components/patient/HealthEducation';
import { AiChatWidget } from '@/components/patient/AiChatWidget';
import {
  Calendar, Video, FileText, Activity, Heart, Bell, ChevronRight, Clock, MapPin, Lightbulb, BookOpen, MessageSquare, Loader2
} from 'lucide-react';
import Link from 'next/link';

interface Appointment {
  id: string; start_time: string; appointment_type?: string; provider_name?: string;
  location?: string; status: string;
}

interface Medication {
  id: string; medication_name: string; dosage?: string; frequency?: string;
  route?: string; start_date?: string; prescribed_by?: string; status: string;
}

interface LabResult {
  id: string; order_description: string; result_value: string; result_unit?: string;
  reference_range_low?: string; reference_range_high?: string; ordered_datetime: string;
}

const healthTips = [
  'Drink at least 8 glasses of clean water daily to prevent dehydration and urinary tract infections.',
  'Sleep under an insecticide-treated net every night to protect against malaria.',
  'Wash your hands with soap and clean water before eating and after using the toilet.',
  'Take your medications at the same time each day to build a healthy routine.',
  'Eat fruits and vegetables rich in vitamin C to boost your immune system.',
  'Walk for at least 30 minutes a day to maintain heart health and healthy blood pressure.',
];

export default function PatientDashboard() {
  const [chatOpen, setChatOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [medications, setMedications] = useState<Medication[]>([]);
  const [labResults, setLabResults] = useState<LabResult[]>([]);
  const [tipOfDay] = useState(() => healthTips[Math.floor(Math.random() * healthTips.length)]);
  const token = useAuthStore((s) => s.accessToken);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [aptRes, labRes] = await Promise.all([
        fetch('/api/v1/appointments?per_page=10', { headers }),
        fetch('/api/v1/emr/orders?status=completed&per_page=10', { headers }),
      ]);
      if (aptRes.ok) {
        const data = await aptRes.json();
        setAppointments(data.items || data || []);
      }
      if (labRes.ok) {
        const data = await labRes.json();
        setLabResults(data.items || data || []);
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
      <AiChatWidget open={chatOpen} onOpenChange={setChatOpen} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Heart className="h-6 w-6 text-healthcare-green" />
            My Health Dashboard
          </h1>
          <p className="text-muted-foreground">Welcome back! Here&apos;s your health summary.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setChatOpen(true)} className="gap-2">
            <MessageSquare className="h-4 w-4" />AI Assistant
          </Button>
          <Button asChild className="bg-healthcare-green hover:bg-healthcare-green-dark">
            <Link href="/telemedicine"><Video className="h-4 w-4 mr-1" />Start Telemedicine</Link>
          </Button>
        </div>
      </div>

      <Card className="bg-gradient-to-r from-healthcare-green/10 to-blue-50 border-healthcare-green/20">
        <CardContent className="p-4 flex items-start gap-3">
          <Lightbulb className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-amber-600 uppercase tracking-wide">Health Tip of the Day</p>
            <p className="text-sm mt-1">{tipOfDay}</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Upcoming Appointments', value: appointments.filter((a) => a.status === 'scheduled' || a.status === 'confirmed').length.toString(), icon: Calendar, color: 'text-blue-600 bg-blue-100' },
          { label: 'Active Medications', value: medications.filter((m) => m.status === 'active' || m.status === 'prescribed').length.toString(), icon: Activity, color: 'text-green-600 bg-green-100' },
          { label: 'Lab Results', value: labResults.length.toString(), icon: FileText, color: 'text-purple-600 bg-purple-100' },
          { label: 'Health Resources', value: '6', icon: BookOpen, color: 'text-amber-600 bg-amber-100' },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardContent className="p-4 flex items-center gap-4">
              <div className={`w-12 h-12 rounded-lg ${color} flex items-center justify-center`}><Icon className="h-6 w-6" /></div>
              <div><p className="text-2xl font-bold">{value}</p><p className="text-xs text-muted-foreground">{label}</p></div>
            </CardContent>
          </Card>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2"><Calendar className="h-5 w-5 text-healthcare-blue" />Upcoming Appointments</CardTitle>
                <Button variant="ghost" size="sm" asChild><Link href="/appointments">View All <ChevronRight className="h-4 w-4 ml-1" /></Link></Button>
              </CardHeader>
              <CardContent>
                {appointments.filter((a) => a.status === 'scheduled' || a.status === 'confirmed').length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">No upcoming appointments</p>
                ) : (
                  <div className="space-y-3">
                    {appointments.filter((a) => a.status === 'scheduled' || a.status === 'confirmed').slice(0, 3).map((apt) => (
                      <div key={apt.id} className="flex items-start gap-4 p-3 rounded-lg border hover:bg-accent/50 transition-colors">
                        <div className="w-14 text-center">
                          <div className="text-lg font-bold text-healthcare-green">{new Date(apt.start_time).getDate()}</div>
                          <div className="text-xs text-muted-foreground">{new Date(apt.start_time).toLocaleDateString('en-ZM', { month: 'short' })}</div>
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{apt.appointment_type || 'Appointment'}</span>
                            <Badge variant={apt.status === 'confirmed' ? 'success' : 'outline'}>{apt.status}</Badge>
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                            {apt.provider_name && <span>{apt.provider_name}</span>}
                            {apt.location && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{apt.location}</span>}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2"><FileText className="h-5 w-5 text-healthcare-blue" />Recent Lab Results</CardTitle>
                <Button variant="ghost" size="sm" asChild><Link href="/laboratory">View All <ChevronRight className="h-4 w-4 ml-1" /></Link></Button>
              </CardHeader>
              <CardContent>
                {labResults.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">No lab results found</p>
                ) : (
                  <div className="space-y-3">
                    {labResults.slice(0, 3).map((lab) => (
                      <div key={lab.id} className="flex items-center justify-between p-3 rounded-lg border">
                        <div>
                          <p className="font-medium text-sm">{lab.order_description}</p>
                          <p className="text-xs text-muted-foreground">{lab.ordered_datetime}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-bold">{lab.result_value || '-'}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Video className="h-5 w-5 text-healthcare-blue" />Telemedicine Access</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">Connect with your healthcare provider from home.</p>
                <Button className="w-full bg-healthcare-green hover:bg-healthcare-green-dark" asChild>
                  <Link href="/telemedicine"><Video className="h-4 w-4 mr-1" />Start Video Call</Link>
                </Button>
                <div className="text-xs text-muted-foreground flex items-center gap-2">
                  <Clock className="h-3 w-3" />Available: Mon-Fri 8:00-17:00
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-lg flex items-center gap-2"><BookOpen className="h-5 w-5 text-healthcare-blue" />Health Resources</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-3">Access health education materials.</p>
                <Button variant="outline" className="w-full" asChild>
                  <Link href="/patient/education">Browse Resources <ChevronRight className="h-4 w-4 ml-1" /></Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
