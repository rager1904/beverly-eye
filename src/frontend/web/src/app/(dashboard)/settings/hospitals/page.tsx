'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Building2, AlertCircle, CheckCircle2, MapPin, Phone, Globe } from 'lucide-react';
import { useAuthStore } from '@/lib/auth';
import { api } from '@/lib/api-client';

const hospitalSchema = z.object({
  name: z.string().min(2, 'Name is required'),
  code: z.string().min(2, 'Code is required'),
  level: z.string().min(1, 'Level is required'),
  province: z.string().min(1, 'Province is required'),
  district: z.string().min(1, 'District is required'),
  city: z.string().optional(),
  address_line: z.string().optional(),
  phone: z.string().optional(),
  email: z.string().email().optional().or(z.literal('')),
  website: z.string().optional(),
  is_active: z.boolean().default(true),
  bed_count: z.coerce.number().int().min(0).default(0),
});

type HospitalForm = z.infer<typeof hospitalSchema>;

const levels = [
  'Health_Post', 'Health_Center', 'District_Hospital', 'Provincial_Hospital',
  'Tertiary_Hospital', 'Specialized_Hospital', 'Level_1', 'Level_2', 'Level_3', 'Level_4',
];

const emptyFacility: HospitalForm = {
  name: '', code: '', level: '', province: '', district: '', city: '', address_line: '',
  phone: '', email: '', website: '', bed_count: 0, is_active: true,
};

interface Hospital {
  id: string;
  name: string;
  code: string;
  level: string;
  province: string;
  district: string;
  city?: string | null;
  address_line?: string | null;
  website?: string | null;
  phone?: string | null;
  email?: string | null;
  bed_count: number;
  is_active: boolean;
}

export default function ManageHospitalsPage() {
  const isAdmin = useAuthStore((state) => state.user?.role === 'admin');
  const [editing, setEditing] = useState<Hospital | null>(null);
  const [archiving, setArchiving] = useState<Hospital | null>(null);
  const editor = useRef<HTMLFormElement>(null);
  const archivePrompt = useRef<HTMLDivElement>(null);
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  const { register, handleSubmit, formState: { errors }, reset, setValue, watch } = useForm<HospitalForm>({
    resolver: zodResolver(hospitalSchema),
    defaultValues: emptyFacility,
  });

  const level = watch('level');

  const fetchHospitals = useCallback(async () => {
    try {
      const data: Hospital[] = await api.get('/hospital/list?include_inactive=true');
      setHospitals(data);
    } catch {
      setResult({ success: false, message: 'Failed to load hospitals' });
    }
    setLoading(false);
  }, []);

  useEffect(() => { if (isAdmin) void fetchHospitals(); }, [fetchHospitals, isAdmin]);
  useEffect(() => { if (editing) editor.current?.scrollIntoView({ block: 'start' }); }, [editing]);
  useEffect(() => { if (archiving) archivePrompt.current?.focus(); }, [archiving]);

  if (!isAdmin) return <p>You need an administrator account to manage facilities.</p>;

  const cancelEdit = () => {
    setEditing(null);
    reset(emptyFacility);
  };

  const editFacility = (facility: Hospital) => {
    setEditing(facility);
    setResult(null);
    reset({
      ...facility,
      city: facility.city ?? '', address_line: facility.address_line ?? '',
      phone: facility.phone ?? '', email: facility.email ?? '', website: facility.website ?? '',
    });
  };

  const onSubmit = async (data: HospitalForm) => {
    setSubmitting(true);
    setResult(null);
    try {
      const { is_active, ...details } = data;
      const payload = {
        ...details,
        email: data.email || null,
        city: data.city || null,
        address_line: data.address_line || null,
        phone: data.phone || null,
        website: data.website || null,
      };
      const saved: Hospital = editing
        ? await api.put(`/hospital/facilities/${editing.id}`, { ...payload, is_active })
        : await api.post('/hospital', payload);
      setHospitals((prev) => editing ? prev.map((h) => h.id === saved.id ? saved : h) : [...prev, saved]);
      setResult({ success: true, message: `Facility "${saved.name}" saved` });
      cancelEdit();
    } catch (error) {
      setResult({
        success: false,
        message: error instanceof Error ? error.message : 'Failed to save facility',
      });
    }
    setSubmitting(false);
  };

  const archiveFacility = async () => {
    if (!archiving) return;
    setSubmitting(true);
    setResult(null);
    try {
      const saved = await api.delete<Hospital>(`/hospital/facilities/${archiving.id}`);
      setHospitals((prev) => prev.map((h) => h.id === saved.id ? saved : h));
      if (editing?.id === saved.id) cancelEdit();
      setResult({ success: true, message: `Facility "${saved.name}" archived` });
      setArchiving(null);
    } catch (error) {
      setResult({ success: false, message: error instanceof Error ? error.message : 'Failed to archive facility' });
    } finally {
      setSubmitting(false);
    }
  };

  const levelLabel = (l: string) => l.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Hospital Management</h1>
          <p className="text-muted-foreground">Manage healthcare facilities and clinics</p>
        </div>
      </div>

      {result && (
        <div className={`p-4 rounded-lg border flex items-start gap-3 ${result.success ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
          {result.success ? <CheckCircle2 className="h-5 w-5 mt-0.5 shrink-0" /> : <AlertCircle className="h-5 w-5 mt-0.5 shrink-0" />}
          <div>
            <p className="font-medium">{result.success ? 'Success' : 'Error'}</p>
            <p className="text-sm mt-1">{result.message}</p>
          </div>
        </div>
      )}

      {archiving && (
        <Card ref={archivePrompt} tabIndex={-1}>
          <CardHeader>
            <CardTitle>Archive {archiving.name}?</CardTitle>
            <CardDescription>It will be hidden from active facility lists. Linked records are kept, and you can reactivate it here.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button variant="destructive" disabled={submitting} onClick={archiveFacility}>Archive facility</Button>
            <Button variant="outline" disabled={submitting} onClick={() => setArchiving(null)}>Cancel</Button>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Plus className="h-4 w-4" /> {editing ? `Edit ${editing.name}` : 'Add New Facility'}
            </CardTitle>
            <CardDescription>Register a hospital, clinic, or health post</CardDescription>
          </CardHeader>
          <CardContent>
            <form ref={editor} onSubmit={handleSubmit(onSubmit)} className="scroll-mt-20 space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1 sm:col-span-2">
                  <label className="text-sm font-medium">Facility Name</label>
                  <Input {...register('name')} placeholder="e.g. Eye & Dental Hospital" />
                  {errors.name && <p className="text-xs text-red-500">{errors.name.message}</p>}
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Code</label>
                  <Input {...register('code')} placeholder="e.g. EDH001" />
                  {errors.code && <p className="text-xs text-red-500">{errors.code.message}</p>}
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Level</label>
                  <Select onValueChange={(v) => setValue('level', v)} value={level}>
                    <SelectTrigger><SelectValue placeholder="Select level" /></SelectTrigger>
                    <SelectContent>
                      {levels.map((l) => <SelectItem key={l} value={l}>{levelLabel(l)}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <input type="hidden" {...register('level')} />
                  {errors.level && <p className="text-xs text-red-500">{errors.level.message}</p>}
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Province</label>
                  <Input {...register('province')} placeholder="e.g. Lusaka" />
                  {errors.province && <p className="text-xs text-red-500">{errors.province.message}</p>}
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">District</label>
                  <Input {...register('district')} placeholder="e.g. Lusaka" />
                  {errors.district && <p className="text-xs text-red-500">{errors.district.message}</p>}
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">City</label>
                  <Input {...register('city')} placeholder="Optional" />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Phone</label>
                  <Input {...register('phone')} placeholder="+260 ..." />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Email</label>
                  <Input type="email" {...register('email')} placeholder="admin@hospital.zm" />
                </div>
                <label className="space-y-1 text-sm font-medium">
                  <span>Address</span><Input {...register('address_line')} />
                </label>
                <label className="space-y-1 text-sm font-medium">
                  <span>Website</span><Input {...register('website')} />
                </label>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Bed Count</label>
                  <Input type="number" {...register('bed_count')} placeholder="0" />
                </div>
              </div>
              {editing && (
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" {...register('is_active')} /> Active facility
                </label>
              )}
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={submitting || !!archiving}>
                  {submitting ? 'Saving...' : editing ? 'Save changes' : 'Create Facility'}
                </Button>
                {editing && <Button type="button" variant="outline" disabled={submitting} onClick={cancelEdit}>Cancel edit</Button>}
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">Registered Facilities ({hospitals.length})</h3>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : hospitals.length === 0 ? (
            <p className="text-sm text-muted-foreground">No facilities registered yet.</p>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {hospitals.map((h) => (
                <div key={h.id} className="p-4 rounded-lg border">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-healthcare-green" />
                        <p className="font-medium text-sm">{h.name}</p>
                        <span className="text-xs bg-muted px-2 py-0.5 rounded-full">{h.code}</span>
                      </div>
                      <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                        <p className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {h.district}, {h.province}</p>
                        <p>{levelLabel(h.level)} &middot; {h.bed_count} beds</p>
                        {h.phone && <p className="flex items-center gap-1"><Phone className="h-3 w-3" /> {h.phone}</p>}
                        {h.email && <p className="flex items-center gap-1"><Globe className="h-3 w-3" /> {h.email}</p>}
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span className="mr-auto text-xs text-muted-foreground">{h.is_active ? 'Active' : 'Archived'}</span>
                    <Button size="sm" variant="outline" disabled={submitting || !!archiving} onClick={() => editFacility(h)}>Edit</Button>
                    {h.is_active && (
                      <Button size="sm" variant="outline" disabled={submitting || !!archiving} onClick={() => setArchiving(h)}>Archive</Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
