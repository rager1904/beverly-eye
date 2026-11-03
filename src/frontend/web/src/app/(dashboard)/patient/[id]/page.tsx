'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { User, ArrowLeft, Loader2, Calendar, Phone, Mail, MapPin, Activity, FileText, Pill, AlertTriangle, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { formatDateTime } from '@/lib/utils';
import { usePatientJourneys } from '@/hooks/usePatientFlow';
import { journeyStatusVariant, priorityVariant, servicePointLabel } from '@/components/patient-flow/flow-utils';

interface PatientDetail {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone: string;
  email: string;
  address_line: string;
  city: string;
  district: string;
  province: string;
  occupation: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
}

export default function PatientDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [patient, setPatient] = useState<PatientDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const patientId = Array.isArray(params?.id) ? params.id[0] ?? '' : params?.id ?? '';
  const { data: journeys, isLoading: journeysLoading } = usePatientJourneys(patientId);

  const fetchPatient = useCallback(async () => {
    setLoading(true);
    try {
      const token = useAuthStore.getState().accessToken;
      const res = await fetch(`/api/v1/emr/patients/${params.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setPatient(data.data || data);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => { fetchPatient(); }, [fetchPatient]);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>;
  }

  if (!patient) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" asChild><Link href="/patient"><ArrowLeft className="h-4 w-4 mr-1" />Back</Link></Button>
        <Card><CardContent className="text-center py-12">
          <User className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="text-lg font-medium">Patient not found</p>
        </CardContent></Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/patient"><ArrowLeft className="h-4 w-4 mr-1" />Back to Patients</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <User className="h-6 w-6 text-healthcare-blue" />
            {patient.first_name} {patient.last_name}
          </h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push(`/emr/edit-patient?id=${patient.id}`)}>Edit Patient</Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Personal Information</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2"><Calendar className="h-4 w-4 text-muted-foreground" /><span className="text-sm">{patient.date_of_birth}</span></div>
              <div className="flex items-center gap-2"><User className="h-4 w-4 text-muted-foreground" /><span className="text-sm capitalize">{patient.gender}</span></div>
              <div className="flex items-center gap-2"><Phone className="h-4 w-4 text-muted-foreground" /><span className="text-sm">{patient.phone}</span></div>
              {patient.email && <div className="flex items-center gap-2"><Mail className="h-4 w-4 text-muted-foreground" /><span className="text-sm">{patient.email}</span></div>}
              <div className="flex items-center gap-2"><MapPin className="h-4 w-4 text-muted-foreground" /><span className="text-sm">{patient.address_line || ''} {patient.city || ''} {patient.district || ''} {patient.province || ''}</span></div>
              {patient.occupation && <div><p className="text-sm text-muted-foreground mt-2">Occupation</p><p className="text-sm">{patient.occupation}</p></div>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Quick Actions</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              <Button className="w-full justify-start" variant="outline" onClick={() => router.push(`/patient/${patient.id}/records`)}>
                <FileText className="h-4 w-4 mr-2" />Medical Records
              </Button>
              <Button className="w-full justify-start" variant="outline" onClick={() => router.push(`/patient/${patient.id}/medications`)}>
                <Pill className="h-4 w-4 mr-2" />Medications
              </Button>
              <Button className="w-full justify-start" variant="outline" onClick={() => router.push(`/patient/${patient.id}/allergies`)}>
                <AlertTriangle className="h-4 w-4 mr-2" />Allergies
              </Button>
              <Button className="w-full justify-start" variant="outline" onClick={() => router.push(`/appointments/new?patient=${patient.id}`)}>
                <Calendar className="h-4 w-4 mr-2" />Schedule Appointment
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Tabs defaultValue="overview">
            <TabsList>
              <TabsTrigger value="overview"><Activity className="h-4 w-4 mr-1" />Overview</TabsTrigger>
              <TabsTrigger value="encounters">Encounters</TabsTrigger>
              <TabsTrigger value="visits">Visits</TabsTrigger>
            </TabsList>
            <TabsContent value="overview" className="mt-4">
              <Card>
                <CardHeader><CardTitle>Patient Overview</CardTitle></CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">Select a tab above or use the quick actions to view patient details.</p>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="encounters" className="mt-4">
              <Card>
                <CardHeader><CardTitle>Recent Encounters</CardTitle></CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">No encounters recorded yet.</p>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="visits" className="mt-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Patient Flow Visits</CardTitle>
                  <Button size="sm" variant="outline" asChild>
                    <Link href="/patient-flow">Open queue</Link>
                  </Button>
                </CardHeader>
                <CardContent>
                  {journeysLoading ? (
                    <div className="flex h-24 items-center justify-center">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : !journeys?.length ? (
                    <p className="text-sm text-muted-foreground">No visits recorded yet.</p>
                  ) : (
                    <div className="divide-y">
                      {journeys.map((journey) => (
                        <Link
                          key={journey.id}
                          href={`/patient-flow/${journey.id}`}
                          className="flex flex-wrap items-center justify-between gap-2 py-3 hover:bg-accent/50"
                        >
                          <div>
                            <p className="text-sm font-medium">{journey.journey_number}</p>
                            <p className="text-xs text-muted-foreground">
                              {formatDateTime(journey.checked_in_at)} ·{' '}
                              {servicePointLabel(journey.current_service_point)}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant={priorityVariant(journey.priority)}>{journey.priority}</Badge>
                            <Badge variant={journeyStatusVariant(journey.status)}>
                              {journey.status.replace(/_/g, ' ')}
                            </Badge>
                            <ArrowRight className="h-4 w-4 text-muted-foreground" />
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
