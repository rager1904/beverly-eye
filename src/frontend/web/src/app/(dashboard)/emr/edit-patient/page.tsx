'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { FileText, ArrowLeft, User, Save } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { api } from '@/lib/api-client';

interface PatientRecord {
  id: string;
  smartcare_id?: string | null;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone: string;
  address_line?: string | null;
  district?: string | null;
  province?: string | null;
}

const provinces = [
  { value: 'Lusaka', label: 'Lusaka' },
  { value: 'Copperbelt', label: 'Copperbelt' },
  { value: 'Central', label: 'Central' },
  { value: 'Eastern', label: 'Eastern' },
  { value: 'Northern', label: 'Northern' },
  { value: 'Luapula', label: 'Luapula' },
  { value: 'Muchinga', label: 'Muchinga' },
  { value: 'Southern', label: 'Southern' },
  { value: 'Western', label: 'Western' },
  { value: 'North_Western', label: 'North-Western' },
];

export default function EditPatientPage() {
  const router = useRouter();
  const [patientId, setPatientId] = useState('');
  const [name, setName] = useState('');
  const [nupn, setNupn] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [gender, setGender] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [district, setDistrict] = useState('');
  const [province, setProvince] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) {
      setLoadError('Open this page from a patient record to edit a specific patient.');
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setPatientId(id);
    api.get<PatientRecord>(`/emr/patients/${encodeURIComponent(id)}`, { signal: controller.signal })
      .then((patient) => {
        setName([patient.first_name, patient.last_name].filter(Boolean).join(' '));
        setNupn(patient.smartcare_id || '');
        setDateOfBirth(patient.date_of_birth?.slice(0, 10) || '');
        setGender(patient.gender || '');
        setPhone(patient.phone || '');
        setAddress(patient.address_line || '');
        setDistrict(patient.district || '');
        setProvince(patient.province || '');
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setLoadError(error instanceof Error ? error.message : 'Unable to load patient');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const [firstName, ...lastNameParts] = name.trim().split(/\s+/);
    const lastName = lastNameParts.join(' ');
    if (!patientId || !firstName || !lastName) {
      toast.error('Enter the patient’s first and last name');
      return;
    }
    setSubmitting(true);
    try {
      await api.patch(`/emr/patients/${encodeURIComponent(patientId)}`, {
        smartcare_id: nupn || null,
        first_name: firstName,
        last_name: lastName,
        date_of_birth: dateOfBirth || undefined,
        gender: gender || undefined,
        phone: phone || undefined,
        address_line: address || null,
        district: district || null,
        province: province || null,
      });
      toast.success('Patient information updated');
      router.push(`/patient/${patientId}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to update patient');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="flex min-h-64 items-center justify-center text-sm text-muted-foreground">Loading patient record…</div>;
  }

  if (loadError || !patientId) {
    return (
      <div role="alert" className="space-y-3 rounded-md border p-4 text-sm">
        <p>{loadError || 'Open this page from a patient record to edit a specific patient.'}</p>
        <Button variant="outline" asChild><Link href="/emr">Back to EMR</Link></Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/emr"><ArrowLeft className="h-4 w-4 mr-1" />Back to EMR</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <User className="h-6 w-6 text-healthcare-blue" />
            Edit Patient Information
          </h1>
          <p className="text-muted-foreground">Update the selected patient’s saved demographics</p>
        </div>
      </div>

      <Card className="max-w-3xl">
        <CardHeader>
          <CardTitle>Patient Demographics</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Full Name *</label>
                <Input value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">SmartCare ID / NUPN</label>
                <Input value={nupn} onChange={(e) => setNupn(e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Date of Birth</label>
                <Input type="date" value={dateOfBirth} onChange={(e) => setDateOfBirth(e.target.value)} />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Gender</label>
                <div className="flex gap-2">
                  {['male', 'female', 'other'].map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => setGender(g)}
                      className={`flex-1 p-2 rounded-lg border text-sm font-medium capitalize transition-colors ${gender === g ? 'bg-healthcare-green/10 border-healthcare-green text-healthcare-green' : 'bg-background hover:bg-accent'}`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Phone</label>
              <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Address</label>
              <Input value={address} onChange={(e) => setAddress(e.target.value)} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">District</label>
                <Input value={district} onChange={(e) => setDistrict(e.target.value)} />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Province</label>
                <select
                  value={province}
                  onChange={(e) => setProvince(e.target.value)}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="">Select province</option>
                  {provinces.map((p) => (<option key={p.value} value={p.value}>{p.label}</option>))}
                </select>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="submit" className="bg-healthcare-green hover:bg-healthcare-green-dark" disabled={submitting || loading}>
                <Save className="h-4 w-4 mr-1" />{submitting ? 'Saving...' : 'Save Changes'}
              </Button>
              <Button type="button" variant="outline" asChild>
                <Link href="/emr">Cancel</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
