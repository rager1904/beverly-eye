'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/lib/auth';
import { clinicalApi } from '@/lib/clinical-api';
import { PatientPicker } from '@/components/PatientPicker';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface Ward { id: string; name: string }
interface Bed { id: string; ward_id: string; bed_label: string; current_encounter_id: string }

export default function AdmitPatientPage() {
  const role = useAuthStore(s => s.user?.role);
  const [patient, setPatient] = useState('');
  const [wards, setWards] = useState<Ward[]>([]);
  const [beds, setBeds] = useState<Bed[]>([]);
  const [ward, setWard] = useState('');
  const [bed, setBed] = useState('');
  const [reason, setReason] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [admitted, setAdmitted] = useState<Bed | null>(null);
  const allowed = role === 'provider' || role === 'nurse' || role === 'admin';
  useEffect(() => {
    if (!allowed) return;
    const controller = new AbortController();
    Promise.all([
      clinicalApi<Ward[]>('hospital/wards', { signal: controller.signal }),
      clinicalApi<Bed[]>('hospital/wards/beds/available', { signal: controller.signal }),
    ]).then(([w, b]) => { setWards(w); setBeds(b); })
      .catch(err => { if (!controller.signal.aborted) setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [allowed]);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError('');
    try {
      setAdmitted(await clinicalApi<Bed>(`hospital/wards/beds/${bed}/admit`, {
        method: 'POST', body: JSON.stringify({ patient_id: patient, reason: reason.trim(), notes: notes.trim() || null }),
      }));
    } catch (err) { setError(err instanceof Error ? err.message : 'Admission failed'); }
    finally { setBusy(false); }
  }
  if (!allowed) return <p role="alert">Admissions are available to doctors, nurses and administrators.</p>;
  return <div className="space-y-6 max-w-3xl">
    <Button variant="outline" asChild><Link href="/hospital">Back to hospital</Link></Button>
    <h1 className="text-2xl font-bold">Admit patient</h1>
    <p className="text-muted-foreground">Create an inpatient encounter and allocate an available bed.</p>
    {admitted ? <Card><CardHeader><CardTitle>Admission confirmed</CardTitle></CardHeader><CardContent className="space-y-3">
      <p role="status">Bed {admitted.bed_label} has been allocated.</p>
      <p className="text-sm break-all">Encounter: {admitted.current_encounter_id}</p>
      <Button asChild><Link href="/emr">Open medical records</Link></Button>
    </CardContent></Card> : <Card><CardHeader><CardTitle>Admission details</CardTitle></CardHeader><CardContent>
      <form onSubmit={submit} className="space-y-4">
        <PatientPicker value={patient} onChange={setPatient} />
        {loading ? <p role="status">Loading wards and beds…</p> : <>
          <label className="block" htmlFor="ward">Ward *</label>
          <select id="ward" required className="w-full rounded-md border bg-background p-2" value={ward} onChange={e => { setWard(e.target.value); setBed(''); }}>
            <option value="">Select ward</option>{wards.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <label className="block" htmlFor="bed">Available bed *</label>
          <select id="bed" required disabled={!ward} className="w-full rounded-md border bg-background p-2" value={bed} onChange={e => setBed(e.target.value)}>
            <option value="">Select bed</option>{beds.filter(b => b.ward_id === ward).map(b => <option key={b.id} value={b.id}>{b.bed_label}</option>)}
          </select>
          {ward && !beds.some(b => b.ward_id === ward) && <p>No available beds in this ward.</p>}
        </>}
        <label htmlFor="reason" className="block">Reason for admission *</label>
        <Textarea id="reason" required maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} />
        <label htmlFor="notes" className="block">Clinical notes</label>
        <Textarea id="notes" maxLength={5000} value={notes} onChange={e => setNotes(e.target.value)} />
        {error && <p role="alert" className="text-red-600">{error}</p>}
        <Button disabled={busy || loading || !bed || !patient || !reason.trim()}>{busy ? 'Admitting…' : 'Confirm admission'}</Button>
      </form>
    </CardContent></Card>}
  </div>;
}
