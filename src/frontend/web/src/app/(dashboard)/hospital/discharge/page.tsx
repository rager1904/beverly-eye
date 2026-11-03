'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Building2, ArrowLeft, LogOut } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

const dischargeReasons = ['Recovered', 'Transferred', 'Against Medical Advice', 'Deceased', 'Self-Discharge', 'Referred'];

export default function DischargePatientPage() {
  const router = useRouter();
  const [patientName, setPatientName] = useState('');
  const [patientId, setPatientId] = useState('');
  const [reason, setReason] = useState('');
  const [dischargeNotes, setDischargeNotes] = useState('');
  const [followUpDate, setFollowUpDate] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientName || !reason) {
      toast.error('Please fill in patient name and discharge reason');
      return;
    }
    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 800));
    toast.success('Patient discharged successfully');
    router.push('/hospital');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
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
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Patient Name *</label>
                <Input placeholder="Full name" value={patientName} onChange={(e) => setPatientName(e.target.value)} required />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Patient ID / NUPN</label>
                <Input placeholder="e.g. P001" value={patientId} onChange={(e) => setPatientId(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Discharge Reason *</label>
              <div className="flex flex-wrap gap-2">
                {dischargeReasons.map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setReason(r)}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${reason === r ? 'bg-healthcare-green/10 border-healthcare-green text-healthcare-green' : 'bg-background hover:bg-accent'}`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Discharge Summary / Notes</label>
              <Textarea placeholder="Summary of hospital stay, treatment provided, and discharge instructions..." value={dischargeNotes} onChange={(e) => setDischargeNotes(e.target.value)} rows={4} />
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Follow-up Appointment</label>
              <Input type="date" value={followUpDate} onChange={(e) => setFollowUpDate(e.target.value)} />
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
