'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Building2, ArrowLeft, MoveRight } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

const wards = ['General Ward', 'Maternity', 'Pediatrics', 'ICU', 'Surgical', 'Isolation', 'Psychiatric'];
const facilities = ['UTH Lusaka', 'Chainama Clinic', 'Ndola Teaching Hospital', 'Chipata General', 'Livingstone Central'];

export default function TransferPatientPage() {
  const [patientName, setPatientName] = useState('');
  const [patientId, setPatientId] = useState('');
  const [fromWard, setFromWard] = useState('');
  const [toFacility, setToFacility] = useState('');
  const [toWard, setToWard] = useState('');
  const [transferReason, setTransferReason] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientName || !fromWard || !toWard) {
      toast.error('Please fill in patient name and wards');
      return;
    }
    toast.error('Transfer is not connected to the server yet. No transfer was saved.');
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
            <MoveRight className="h-6 w-6 text-healthcare-blue" />
            Transfer Patient
          </h1>
          <p className="text-muted-foreground">Transfer a patient between wards or facilities</p>
          <p role="status" className="mt-1 text-sm text-amber-700">Transfers cannot be submitted yet; the backend does not have a patient-transfer endpoint.</p>
        </div>
      </div>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Transfer Details</CardTitle>
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
              <label className="text-sm font-medium mb-1.5 block">Current Ward *</label>
              <div className="flex flex-wrap gap-2">
                {wards.map((w) => (
                  <button
                    key={w}
                    type="button"
                    onClick={() => setFromWard(w)}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${fromWard === w ? 'bg-red-50 border-red-300 text-red-600' : 'bg-background hover:bg-accent'}`}
                  >
                    {w}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Transfer to Facility</label>
                <select
                  value={toFacility}
                  onChange={(e) => setToFacility(e.target.value)}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="">Same facility</option>
                  {facilities.filter((f) => f !== toFacility).map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Destination Ward *</label>
                <div className="flex flex-wrap gap-2">
                  {wards.filter((w) => w !== fromWard).map((w) => (
                    <button
                      key={w}
                      type="button"
                      onClick={() => setToWard(w)}
                      className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${toWard === w ? 'bg-healthcare-green/10 border-healthcare-green text-healthcare-green' : 'bg-background hover:bg-accent'}`}
                    >
                      {w}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Reason for Transfer</label>
              <Textarea placeholder="Why is this patient being transferred?" value={transferReason} onChange={(e) => setTransferReason(e.target.value)} rows={3} />
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="submit" className="bg-healthcare-green hover:bg-healthcare-green-dark">
                Transfer Patient
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
