'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertTriangle, ArrowLeft, Send } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

const diseases = [
  'Malaria', 'HIV/AIDS', 'Tuberculosis', 'Cholera', 'COVID-19',
  'Measles', 'Polio', 'Ebola', 'Yellow Fever', 'Meningitis',
  'Typhoid', 'Dysentery', 'Rabies', 'Anthrax', 'Plague',
];

const provinces = [
  'Central', 'Copperbelt', 'Eastern', 'Luapula', 'Lusaka',
  'Muchinga', 'Northern', 'North_Western', 'Southern', 'Western',
];

export default function ReportOutbreakPage() {
  const router = useRouter();
  const [disease, setDisease] = useState('');
  const [district, setDistrict] = useState('');
  const [province, setProvince] = useState('');
  const [facility, setFacility] = useState('');
  const [casesCount, setCasesCount] = useState('');
  const [deaths, setDeaths] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!disease || !district || !province || !casesCount) {
      toast.error('Please fill in all required fields');
      return;
    }
    setSubmitting(true);
    try {
      const token = useAuthStore.getState().accessToken;
      const res = await fetch('/api/v1/public-health/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          disease,
          district,
          province,
          facility_name: facility,
          status: 'suspected',
          severity: parseInt(casesCount) > 50 ? 'critical' : parseInt(casesCount) > 20 ? 'high' : 'moderate',
          patient_age: null,
          patient_gender: null,
          outcome: parseInt(deaths) > 0 ? 'dead' : null,
          notes,
        }),
      });
      if (res.ok) {
        toast.success('Outbreak reported successfully');
        router.push('/public-health');
      } else {
        const data = await res.json();
        toast.error(data.detail || 'Failed to report outbreak');
      }
    } catch {
      toast.error('Network error. Please try again.');
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
              <Link href="/public-health"><ArrowLeft className="h-4 w-4 mr-1" />Back</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <AlertTriangle className="h-6 w-6 text-red-500" />
            Report Disease Outbreak
          </h1>
          <p className="text-muted-foreground">Report a potential disease outbreak to the surveillance system</p>
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle>Outbreak Details</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label htmlFor="disease" className="text-sm font-medium">Disease *</label>
                <Select value={disease} onValueChange={setDisease} required>
                  <SelectTrigger><SelectValue placeholder="Select disease" /></SelectTrigger>
                  <SelectContent>
                    {diseases.map((d) => (
                      <SelectItem key={d} value={d}>{d}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label htmlFor="cases" className="text-sm font-medium">Reported Cases *</label>
                <Input id="cases" type="number" min="1" value={casesCount} onChange={(e) => setCasesCount(e.target.value)} required placeholder="Number of cases" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label htmlFor="province" className="text-sm font-medium">Province *</label>
                <Select value={province} onValueChange={setProvince} required>
                  <SelectTrigger><SelectValue placeholder="Select province" /></SelectTrigger>
                  <SelectContent>
                    {provinces.map((p) => (
                      <SelectItem key={p} value={p}>{p.replace('_', ' ')}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label htmlFor="district" className="text-sm font-medium">District *</label>
                <Input id="district" value={district} onChange={(e) => setDistrict(e.target.value)} required placeholder="District name" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label htmlFor="facility" className="text-sm font-medium">Health Facility</label>
                <Input id="facility" value={facility} onChange={(e) => setFacility(e.target.value)} placeholder="Facility name" />
              </div>
              <div className="space-y-2">
                <label htmlFor="deaths" className="text-sm font-medium">Deaths</label>
                <Input id="deaths" type="number" min="0" value={deaths} onChange={(e) => setDeaths(e.target.value)} placeholder="Number of deaths (if any)" />
              </div>
            </div>

            <div className="space-y-2">
                <label htmlFor="notes" className="text-sm font-medium">Additional Notes</label>
              <Textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Any additional information..." rows={3} />
            </div>

            <div className="flex gap-2 justify-end">
              <Button variant="outline" type="button" onClick={() => router.push('/public-health')}>Cancel</Button>
              <Button type="submit" disabled={submitting}>
                <Send className="h-4 w-4 mr-2" />
                {submitting ? 'Submitting...' : 'Report Outbreak'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
