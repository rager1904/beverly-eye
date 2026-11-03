'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { FileText, ArrowLeft, User, Save } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

export default function EditPatientPage() {
  const router = useRouter();
  const [name, setName] = useState('Grace Banda');
  const [nupn, setNupn] = useState('ZM-1985-06-15-00234');
  const [dateOfBirth, setDateOfBirth] = useState('1985-06-15');
  const [gender, setGender] = useState('female');
  const [bloodType, setBloodType] = useState('O+');
  const [phone, setPhone] = useState('+260 97 123 4567');
  const [address, setAddress] = useState('123 Freedom Way, Lusaka');
  const [district, setDistrict] = useState('Lusaka');
  const [province, setProvince] = useState('Lusaka');
  const [allergies, setAllergies] = useState('Penicillin, Sulfa');
  const [chronicConditions, setChronicConditions] = useState('Hypertension, Type 2 Diabetes');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) {
      toast.error('Patient name is required');
      return;
    }
    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 800));
    toast.success('Patient information updated');
    router.push('/emr');
  };

  const bloodTypes = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
  const provinces = ['Lusaka', 'Copperbelt', 'Central', 'Eastern', 'Northern', 'Luapula', 'Muchinga', 'Southern', 'Western', 'North-Western'];

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
          <p className="text-muted-foreground">Update patient demographics and medical information</p>
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
                <label className="text-sm font-medium mb-1.5 block">NUPN</label>
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

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Blood Type</label>
                <div className="flex flex-wrap gap-1">
                  {bloodTypes.map((b) => (
                    <button
                      key={b}
                      type="button"
                      onClick={() => setBloodType(b)}
                      className={`w-10 h-10 rounded-lg border text-xs font-medium transition-colors ${bloodType === b ? 'bg-red-50 border-red-300 text-red-600' : 'bg-background hover:bg-accent'}`}
                    >
                      {b}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Phone</label>
                <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>
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
                  {provinces.map((p) => (<option key={p} value={p}>{p}</option>))}
                </select>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Allergies (comma-separated)</label>
              <Input value={allergies} onChange={(e) => setAllergies(e.target.value)} placeholder="e.g. Penicillin, Sulfa" />
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Chronic Conditions (comma-separated)</label>
              <Input value={chronicConditions} onChange={(e) => setChronicConditions(e.target.value)} placeholder="e.g. Hypertension, Diabetes" />
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="submit" className="bg-healthcare-green hover:bg-healthcare-green-dark" disabled={submitting}>
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
