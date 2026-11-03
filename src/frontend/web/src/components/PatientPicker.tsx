'use client';

import { useEffect, useState } from 'react';
import { clinicalApi } from '@/lib/clinical-api';
import { Input } from '@/components/ui/input';

interface Patient { id: string; first_name: string; last_name: string; nrc_number?: string }

export function PatientPicker({ value, onChange }: { value: string; onChange: (id: string) => void }) {
  const [query, setQuery] = useState('');
  const [patients, setPatients] = useState<Patient[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await clinicalApi<{ items: Patient[] }>(`emr/patients?query=${encodeURIComponent(query)}&per_page=20`, { signal: controller.signal });
        setPatients(data.items);
        setError('');
      } catch (err) {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'Unable to load patients');
      } finally { if (!controller.signal.aborted) setLoading(false); }
    }, 300);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query]);
  return <div className="space-y-2">
    <label htmlFor="patient-search" className="block text-sm font-medium">Find registered patient</label>
    <Input id="patient-search" value={query} onChange={e => { setQuery(e.target.value); onChange(''); }} placeholder="Search name or NRC" />
    <label htmlFor="patient-select" className="block text-sm font-medium">Patient *</label>
    <select id="patient-select" required value={value} onChange={e => onChange(e.target.value)} className="w-full rounded-md border bg-background p-2">
      <option value="">Select patient</option>
      {patients.map(p => <option key={p.id} value={p.id}>{p.first_name} {p.last_name} — {p.nrc_number || p.id}</option>)}
    </select>
    {loading && <p role="status" className="text-sm">Loading patients…</p>}
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
  </div>;
}
