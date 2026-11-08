'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Calendar, ArrowLeft, Video, MapPin } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { PatientPicker } from '@/components/PatientPicker';
import { useCreateAppointment } from '@/hooks/useAppointments';

export default function NewAppointmentPage() {
  const router = useRouter();
  const createAppointment = useCreateAppointment();
  const [patientId, setPatientId] = useState('');
  const [appointmentType, setAppointmentType] = useState('in-person');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [reason, setReason] = useState('');

  useEffect(() => {
    const patient = new URLSearchParams(window.location.search).get('patient');
    if (patient) setPatientId(patient);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId || !date || !time) {
      toast.error('Please fill in all required fields');
      return;
    }
    const startsAt = new Date(`${date}T${time}:00`);
    const endsAt = new Date(startsAt.getTime() + 30 * 60 * 1000);
    if (endsAt.toDateString() !== startsAt.toDateString()) {
      toast.error('Choose a start time that allows the 30-minute appointment to finish that day');
      return;
    }

    try {
      await createAppointment.mutateAsync({
        patient_id: patientId,
        appointment_type: appointmentType === 'telemedicine' ? 'telemedicine' : 'general',
        appointment_date: date,
        start_time: time,
        end_time: endsAt.toTimeString().slice(0, 5),
        duration_minutes: 30,
        reason: reason || undefined,
      });
      toast.success('Appointment created successfully');
      router.push('/appointments');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to create appointment');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/appointments"><ArrowLeft className="h-4 w-4 mr-1" />Back</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <Calendar className="h-6 w-6 text-healthcare-blue" />
            New Appointment
          </h1>
          <p className="text-muted-foreground">Schedule a new patient appointment</p>
        </div>
      </div>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Appointment Details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <PatientPicker value={patientId} onChange={setPatientId} />
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Appointment Type *</label>
              <div className="flex gap-3">
                {[
                  { value: 'in-person', label: 'In-Person', icon: MapPin },
                  { value: 'telemedicine', label: 'Telemedicine', icon: Video },
                ].map(({ value, label, icon: Icon }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setAppointmentType(value)}
                    className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-lg border text-sm font-medium transition-colors ${appointmentType === value ? 'bg-healthcare-green/10 border-healthcare-green text-healthcare-green' : 'bg-background hover:bg-accent'}`}
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Date *</label>
                <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Time *</label>
                <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} required />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Reason for Visit</label>
              <Textarea
                placeholder="Describe the reason for the appointment..."
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
              />
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="submit" className="bg-healthcare-green hover:bg-healthcare-green-dark" disabled={createAppointment.isPending}>
                {createAppointment.isPending ? 'Creating...' : 'Create Appointment'}
              </Button>
              <Button type="button" variant="outline" asChild>
                <Link href="/appointments">Cancel</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
