'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { FacilitySelect } from '@/components/FacilitySelect';
import { useAuthStore } from '@/lib/auth';
import { withFacility } from '@/lib/facility-scope';
import { clinicalApi } from '@/lib/clinical-api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { UserPlus, ArrowLeft, Save, Activity, Stethoscope } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { useFlowDestinations, useStartJourney } from '@/hooks/usePatientFlow';
import type {
  DestinationStaff,
  JourneyPriority,
  PaymentScheme,
  VisitPaymentStatus,
  VisitType,
} from '@/types';

const provinces = ['Central', 'Copperbelt', 'Eastern', 'Luapula', 'Lusaka', 'Muchinga', 'Northern', 'North_Western', 'Southern', 'Western'];
const genders = ['male', 'female'];

const paymentSchemes: { value: PaymentScheme; label: string }[] = [
  { value: 'cash', label: 'Cash' },
  { value: 'nhima', label: 'NHIMA' },
  { value: 'prudential', label: 'Prudential' },
  { value: 'sanlam', label: 'Sanlam' },
  { value: 'madison', label: 'Madison' },
  { value: 'jubilee', label: 'Jubilee' },
  { value: 'employer', label: 'Employer scheme' },
  { value: 'other', label: 'Other' },
];

export default function RegisterPatientPage() {
  const router = useRouter();
  const isAdmin = useAuthStore((state) => state.user?.role === 'admin');
  const [facilityId, setFacilityId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    first_name: '', last_name: '', date_of_birth: '', gender: '',
    phone: '', email: '', address_line: '', city: '', district: '',
    province: '', occupation: '', emergency_contact_name: '', emergency_contact_phone: '',
  });
  const [startJourney, setStartJourney] = useState(true);
  const [priority, setPriority] = useState<JourneyPriority>('routine');
  const [paymentScheme, setPaymentScheme] = useState<PaymentScheme>('cash');
  const [visitType, setVisitType] = useState<VisitType>('new');
  const [paymentStatus, setPaymentStatus] = useState<VisitPaymentStatus>('unpaid');
  const [schemeNumber, setSchemeNumber] = useState('');
  const [servicePoint, setServicePoint] = useState('general');
  const [departmentId, setDepartmentId] = useState('');
  const [providerId, setProviderId] = useState('');
  const [chiefComplaint, setChiefComplaint] = useState('');

  const { data: destinations } = useFlowDestinations(facilityId, !isAdmin || !!facilityId);
  const startJourneyMutation = useStartJourney(facilityId);

  const update = (key: string, value: string) => setForm((prev) => ({ ...prev, [key]: value }));

  const selectedServicePoint = destinations?.service_points.find(
    (point) => point.code === servicePoint
  );

  const staffOptions = useMemo<DestinationStaff[]>(() => {
    const staff = destinations?.staff ?? [];
    if (!departmentId) return staff;
    return staff.filter((member) => member.department_id === departmentId);
  }, [destinations?.staff, departmentId]);

  const chooseProvider = (value: string) => {
    setProviderId(value);
    const member = destinations?.staff.find((item) => item.id === value);
    if (member?.department_id) setDepartmentId(member.department_id);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.first_name || !form.last_name || !form.date_of_birth || !form.gender || !form.phone) {
      toast.error('Please fill in all required fields');
      return;
    }
    if (isAdmin && !facilityId) {
      toast.error('Select a facility before registering the patient');
      return;
    }
    if (startJourney && !selectedServicePoint) {
      toast.error('Wait for routing options or turn off visit routing to register now');
      return;
    }
    setSubmitting(true);
    try {
      // Optional form fields start as empty strings; omit them so Pydantic
      // does not try to validate "" as an email, province enum, etc.
      const payload = Object.fromEntries(
        Object.entries(form).filter(([, value]) => value !== '')
      );
      const patientPayload: Record<string, unknown> = { ...payload };
      // Mirror the billing scheme onto the patient's insurance record so the
      // cover is visible outside the visit as well.
      if (paymentScheme === 'nhima') {
        patientPayload.nhima_member = true;
        if (schemeNumber) patientPayload.nhima_number = schemeNumber;
      } else if (paymentScheme !== 'cash') {
        const schemeLabel =
          paymentSchemes.find((item) => item.value === paymentScheme)?.label ?? paymentScheme;
        patientPayload.insurance_provider = schemeLabel;
        if (schemeNumber) patientPayload.insurance_number = schemeNumber;
      }
      const patient = await clinicalApi<{ id: string }>(withFacility('emr/patients', facilityId), {
        method: 'POST',
        body: JSON.stringify(patientPayload),
      });
      if (!patient?.id) throw new Error('The server did not confirm registration.');

      if (startJourney && selectedServicePoint) {
        const department = destinations?.departments.find((item) => item.id === departmentId);
        const provider = destinations?.staff.find((item) => item.id === providerId);
        try {
          const journey = await startJourneyMutation.mutateAsync({
            patient_id: patient.id,
            priority,
            payment_scheme: paymentScheme,
            visit_type: visitType,
            payment_status: paymentStatus,
            scheme_number: schemeNumber || undefined,
            chief_complaint: chiefComplaint || undefined,
            step_type: selectedServicePoint.step_type,
            service_point: selectedServicePoint.code,
            department_id: department?.id,
            department_name: department?.name,
            provider_id: provider?.user_id || provider?.id,
            provider_name: provider?.name,
            reason: 'Registered at reception',
          });
          toast.success(`Patient registered and routed (${journey.journey_number})`);
          router.push(withFacility(`/patient-flow/${journey.id}`, facilityId));
          return;
        } catch (error) {
          toast.warning(
            `Patient registered, but routing failed: ${
              error instanceof Error ? error.message : 'unknown error'
            }`
          );
          router.push('/patient-flow');
          return;
        }
      }

      toast.success('Patient registered successfully');
      router.push('/patient');
    } catch (error) {
      if (error instanceof TypeError || error instanceof SyntaxError) {
        toast.error('Could not confirm registration. Check the patient list before submitting again.');
      } else {
        toast.error(error instanceof Error ? error.message : 'Registration failed.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/patient"><ArrowLeft className="h-4 w-4 mr-1" />Back</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <UserPlus className="h-6 w-6 text-healthcare-blue" />
            Register Patient
          </h1>
          <p className="text-muted-foreground">Register a new patient into the system</p>
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle>Patient Information</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {isAdmin && <FacilitySelect value={facilityId} disabled={submitting} onChange={(value) => {
              setFacilityId(value);
              setServicePoint('general');
              setDepartmentId('');
              setProviderId('');
            }} />}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">First Name *</label>
                <Input value={form.first_name} onChange={(e) => update('first_name', e.target.value)} required placeholder="First name" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Last Name *</label>
                <Input value={form.last_name} onChange={(e) => update('last_name', e.target.value)} required placeholder="Last name" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Date of Birth *</label>
                <Input type="date" value={form.date_of_birth} onChange={(e) => update('date_of_birth', e.target.value)} required />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Gender *</label>
                <Select value={form.gender} onValueChange={(v) => update('gender', v)} required>
                  <SelectTrigger><SelectValue placeholder="Select gender" /></SelectTrigger>
                  <SelectContent>
                    {genders.map((g) => <SelectItem key={g} value={g}>{g.charAt(0).toUpperCase() + g.slice(1)}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Phone *</label>
                <Input value={form.phone} onChange={(e) => update('phone', e.target.value)} required placeholder="+260 XXX XXX XXX" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Email</label>
                <Input type="email" value={form.email} onChange={(e) => update('email', e.target.value)} placeholder="email@example.com" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Address</label>
                <Input value={form.address_line} onChange={(e) => update('address_line', e.target.value)} placeholder="Street address" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">City</label>
                <Input value={form.city} onChange={(e) => update('city', e.target.value)} placeholder="City" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">District</label>
                <Input value={form.district} onChange={(e) => update('district', e.target.value)} placeholder="District" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Province</label>
                <Select value={form.province} onValueChange={(v) => update('province', v)}>
                  <SelectTrigger><SelectValue placeholder="Select province" /></SelectTrigger>
                  <SelectContent>
                    {provinces.map((p) => <SelectItem key={p} value={p}>{p.replace('_', ' ')}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Occupation</label>
              <Input value={form.occupation} onChange={(e) => update('occupation', e.target.value)} placeholder="Occupation" />
            </div>

            <div className="border-t my-4" />
            <h3 className="text-sm font-medium">Emergency Contact</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Contact Name</label>
                <Input value={form.emergency_contact_name} onChange={(e) => update('emergency_contact_name', e.target.value)} placeholder="Full name" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Contact Phone</label>
                <Input value={form.emergency_contact_phone} onChange={(e) => update('emergency_contact_phone', e.target.value)} placeholder="+260 XXX XXX XXX" />
              </div>
            </div>

            <div className="border-t my-4" />
            <div className="rounded-lg border bg-muted/30 p-4 space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-semibold">
                    <Activity className="h-4 w-4 text-healthcare-green" />
                    Start patient journey
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Route the patient to a counter, department or clinician straight after registration.
                  </p>
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={startJourney}
                    onChange={(e) => setStartJourney(e.target.checked)}
                    className="h-4 w-4 rounded border-input accent-primary"
                  />
                  Enable
                </label>
              </div>

              {startJourney && (
                <>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Payment scheme</label>
                      <Select
                        value={paymentScheme}
                        onValueChange={(v) => setPaymentScheme(v as PaymentScheme)}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {paymentSchemes.map((scheme) => (
                            <SelectItem key={scheme.value} value={scheme.value}>
                              {scheme.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">Visit type</label>
                      <Select value={visitType} onValueChange={(v) => setVisitType(v as VisitType)}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="new">New visit</SelectItem>
                          <SelectItem value="review">Review</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">Payment status</label>
                      <Select
                        value={paymentStatus}
                        onValueChange={(v) => setPaymentStatus(v as VisitPaymentStatus)}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="paid">Paid</SelectItem>
                          <SelectItem value="unpaid">Unpaid</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {paymentScheme !== 'cash' && (
                    <div className="space-y-2">
                      <label className="text-sm font-medium">
                        {paymentScheme === 'nhima' ? 'NHIMA number' : 'Scheme / member number'}
                      </label>
                      <Input
                        maxLength={50}
                        value={schemeNumber}
                        onChange={(e) => setSchemeNumber(e.target.value)}
                        placeholder={
                          paymentScheme === 'nhima'
                            ? 'NHIMA membership number'
                            : 'Policy or member number'
                        }
                      />
                    </div>
                  )}

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Priority</label>
                      <Select value={priority} onValueChange={(v) => setPriority(v as JourneyPriority)}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="routine">Routine</SelectItem>
                          <SelectItem value="urgent">Urgent</SelectItem>
                          <SelectItem value="emergency">Emergency</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">Send to service point</label>
                      <Select value={servicePoint} onValueChange={setServicePoint}>
                        <SelectTrigger><SelectValue placeholder="Select service point" /></SelectTrigger>
                        <SelectContent>
                          {(destinations?.service_points ?? []).map((point) => (
                            <SelectItem key={point.code} value={point.code}>{point.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">Department</label>
                      <Select
                        value={departmentId || 'none'}
                        onValueChange={(v) => {
                          setDepartmentId(v === 'none' ? '' : v);
                          setProviderId('');
                        }}
                      >
                        <SelectTrigger><SelectValue placeholder="Any department" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">Any department</SelectItem>
                          {(destinations?.departments ?? []).map((department) => (
                            <SelectItem key={department.id} value={department.id}>{department.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">Doctor / nurse</label>
                      <Select
                        value={providerId || 'none'}
                        onValueChange={(v) => chooseProvider(v === 'none' ? '' : v)}
                      >
                        <SelectTrigger><SelectValue placeholder="Any available clinician" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">Any available clinician</SelectItem>
                          {staffOptions.map((member) => (
                            <SelectItem key={member.id} value={member.id}>
                              <span className="flex items-center gap-2">
                                <Stethoscope className="h-3.5 w-3.5" />
                                {member.name} · {member.role.replace('_', ' ')}
                              </span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Chief complaint</label>
                    <Input
                      value={chiefComplaint}
                      onChange={(e) => setChiefComplaint(e.target.value)}
                      placeholder="Why has the patient come in today?"
                    />
                  </div>
                </>
              )}
            </div>

            <div className="flex gap-2 justify-end pt-4">
              <Button variant="outline" type="button" onClick={() => router.push('/patient')}>Cancel</Button>
              <Button type="submit" disabled={submitting}>
                <Save className="h-4 w-4 mr-2" />{submitting ? 'Registering...' : 'Register Patient'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
