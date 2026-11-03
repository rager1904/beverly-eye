'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/lib/auth';
import { clinicalApi } from '@/lib/clinical-api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

interface Order { id: string; patient_id: string; order_code: string; order_description: string; status: string; specimen_id?: string }
interface Result { id: string; result_description: string; result_value: string; result_unit?: string; interpretation: string; verified_by?: string }

export default function LabOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const role = useAuthStore(s => s.user?.role);
  const [order, setOrder] = useState<Order | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [specimen, setSpecimen] = useState('');
  const [value, setValue] = useState('');
  const [unit, setUnit] = useState('');
  const [interpretation, setInterpretation] = useState('normal');
  const technician = role === 'lab_tech' || role === 'admin';
  const collect = technician || role === 'nurse';
  const load = useCallback(async () => {
    const [o, r] = await Promise.all([
      clinicalApi<Order>(`emr/orders/${id}`), clinicalApi<Result[]>(`emr/orders/${id}/results`),
    ]);
    setOrder(o); setResults(r);
  }, [id]);
  useEffect(() => { load().catch(err => setError(err.message)).finally(() => setLoading(false)); }, [load]);
  async function action(path: string, body?: object) {
    if (busy) return;
    setBusy(true); setError('');
    try { await clinicalApi(`emr/orders/${id}/${path}`, { method: 'POST', body: body ? JSON.stringify(body) : undefined }); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Action failed'); }
    finally { setBusy(false); }
  }
  if (loading) return <p role="status">Loading laboratory request…</p>;
  return <div className="space-y-6">
    <Button variant="outline" asChild><Link href="/laboratory">Back to laboratory</Link></Button>
    {error && <p role="alert" className="text-red-600">{error}</p>}
    {order && <>
      <h1 className="text-2xl font-bold">{order.order_description}</h1><Badge variant="outline">{order.status.replaceAll('_', ' ')}</Badge>
      <Card><CardHeader><CardTitle>Request and specimen</CardTitle></CardHeader><CardContent className="space-y-3">
        <p>Patient ID: {order.patient_id}</p>
        <p>Test code: {order.order_code}</p><p>Specimen: {order.specimen_id || 'Awaiting collection'}</p>
        {collect && order.status === 'ordered' && <form className="flex gap-2" onSubmit={e => { e.preventDefault(); action('specimen/collect', { specimen_id: specimen.trim() }); }}>
          <Input aria-label="Specimen barcode" placeholder="Specimen barcode" required maxLength={100} value={specimen} onChange={e => setSpecimen(e.target.value)} />
          <Button disabled={busy || !specimen.trim()}>Record collection</Button>
        </form>}
        {collect && order.status === 'collected' && <Button disabled={busy} onClick={() => action('specimen/receive', {})}>Receive specimen</Button>}
        {technician && order.status === 'received' && <Button disabled={busy} onClick={() => action('start')}>Start processing</Button>}
        {(role === 'provider' || role === 'admin') && ['ordered', 'collected', 'received', 'in_progress'].includes(order.status) && <Button variant="destructive" disabled={busy} onClick={() => { if (window.confirm('Cancel this laboratory request?')) action('cancel'); }}>Cancel request</Button>}
      </CardContent></Card>
      {technician && ['received', 'in_progress'].includes(order.status) && <Card><CardHeader><CardTitle>Enter test result</CardTitle></CardHeader><CardContent>
        <form className="space-y-3" onSubmit={e => { e.preventDefault(); action('results', { order_id: id, patient_id: order.patient_id, result_type: 'lab', result_code: order.order_code, result_description: order.order_description, result_value: value.trim(), result_unit: unit || null, interpretation }); }}>
          <label htmlFor="result-value" className="block">Result value *</label><Input id="result-value" required value={value} onChange={e => setValue(e.target.value)} />
          <label htmlFor="result-unit" className="block">Unit</label><Input id="result-unit" maxLength={50} value={unit} onChange={e => setUnit(e.target.value)} />
          <label htmlFor="interpretation" className="block">Interpretation</label><select id="interpretation" value={interpretation} onChange={e => setInterpretation(e.target.value)} className="rounded border p-2 bg-background">
            {['normal', 'abnormal', 'critical', 'not_interpreted'].map(v => <option key={v} value={v}>{v.replaceAll('_', ' ')}</option>)}
          </select><div><Button disabled={busy || !value.trim()}>Submit result</Button></div>
        </form>
      </CardContent></Card>}
      <Card><CardHeader><CardTitle>Results {order.status !== 'verified' && results.length > 0 ? '(awaiting verification)' : ''}</CardTitle></CardHeader><CardContent className="space-y-4">
        {results.length === 0 ? <p>No results entered.</p> : results.map(r => <div key={r.id} className="border rounded p-4"><p className="font-medium">{r.result_description}</p><p className="text-xl">{r.result_value} {r.result_unit}</p><Badge variant={r.interpretation === 'critical' ? 'destructive' : 'outline'}>{r.interpretation}</Badge><p className="text-sm mt-2">{r.verified_by ? `Verified by ${r.verified_by}` : 'Unverified'}</p></div>)}
        {technician && order.status === 'resulted' && <Button disabled={busy} onClick={() => { if (window.confirm('Confirm these results have been reviewed and are correct?')) action('verify'); }}>Verify results</Button>}
      </CardContent></Card>
    </>}
  </div>;
}
