'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Building2, ArrowLeft, LogOut } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { api } from '@/lib/api-client';

export default function DischargePatientPage() {
  const router = useRouter();
  const [encounterId, setEncounterId] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!encounterId.trim()) {
      toast.error('Enter the active encounter ID');
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/emr/encounters/${encodeURIComponent(encounterId.trim())}/discharge`);
      toast.success('Patient discharged successfully');
      router.push('/emr');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to discharge patient');
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
              <Link href="/hospital"><ArrowLeft className="h-4 w-4 mr-1" />Back</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <LogOut className="h-6 w-6 text-healthcare-blue" />
            Discharge Patient
          </h1>
          <p className="text-muted-foreground">Process patient discharge from the hospital</p>
        </div>
      </div>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Discharge Details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="text-sm font-medium mb-1.5 block">Active Encounter ID *</label>
              <Input placeholder="Encounter UUID from the patient record" value={encounterId} onChange={(e) => setEncounterId(e.target.value)} required />
              <p className="mt-1 text-xs text-muted-foreground">Only an encounter ID is accepted here; the discharge is saved before this page navigates away.</p>
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="submit" className="bg-healthcare-green hover:bg-healthcare-green-dark" disabled={submitting}>
                {submitting ? 'Processing...' : 'Discharge Patient'}
              </Button>
              <Button type="button" variant="outline" asChild>
                <Link href="/hospital">Cancel</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
