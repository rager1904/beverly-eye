'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Pill, Search, ArrowLeft, Loader2, Clock, CheckCircle2, XCircle, Eye } from 'lucide-react';
import Link from 'next/link';
import { formatDateTime } from '@/lib/utils';

interface Prescription {
  id: string;
  medication_name: string;
  patient_name?: string;
  dosage?: string;
  frequency?: string;
  quantity?: number;
  status: string;
  prescribed_by?: string;
  prescribed_at?: string;
  refills?: number;
}

export default function PrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchPrescriptions = useCallback(async () => {
    setLoading(true);
    try {
      const token = useAuthStore.getState().accessToken;
      const res = await window.fetch('/api/v1/emr/orders?order_type=prescription', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setPrescriptions(data.items || data || []);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPrescriptions(); }, [fetchPrescriptions]);

  const filtered = prescriptions.filter((p) =>
    (p.medication_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (p.patient_name || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const pending = prescriptions.filter((p) => p.status === 'prescribed' || p.status === 'ordered');
  const fulfilled = prescriptions.filter((p) => p.status === 'administered' || p.status === 'completed');

  const statusBadge = (s: string) => {
    switch (s) {
      case 'prescribed': return <Badge variant="outline" className="bg-blue-100 text-blue-800">{s}</Badge>;
      case 'administered': return <Badge variant="outline" className="bg-green-100 text-green-800">{s}</Badge>;
      case 'completed': return <Badge variant="outline" className="bg-gray-100 text-gray-800">{s}</Badge>;
      case 'discontinued': return <Badge variant="destructive">{s}</Badge>;
      default: return <Badge variant="outline">{s}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild><Link href="/pharmacy"><ArrowLeft className="h-4 w-4 mr-1" />Back to Pharmacy</Link></Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <Pill className="h-6 w-6 text-green-600" />Prescriptions
          </h1>
          <p className="text-muted-foreground">Manage and fulfill patient prescriptions</p>
        </div>
      </div>

      <div className="grid gap-4 grid-cols-2 lg:grid-cols-3">
        {[
          { label: 'Total Prescriptions', value: prescriptions.length.toString(), icon: Pill, color: 'text-blue-600 bg-blue-100' },
          { label: 'Pending Fulfillment', value: pending.length.toString(), icon: Clock, color: 'text-amber-600 bg-amber-100' },
          { label: 'Fulfilled', value: fulfilled.length.toString(), icon: CheckCircle2, color: 'text-green-600 bg-green-100' },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardContent className="p-4 flex items-center gap-4">
              <div className={`w-12 h-12 rounded-lg ${color} flex items-center justify-center`}><Icon className="h-6 w-6" /></div>
              <div><p className="text-2xl font-bold">{value}</p><p className="text-xs text-muted-foreground">{label}</p></div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        <Input placeholder="Search prescriptions..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-10" />
      </div>

      <Tabs defaultValue="all">
        <TabsList>
          <TabsTrigger value="all">All ({prescriptions.length})</TabsTrigger>
          <TabsTrigger value="pending">Pending ({pending.length})</TabsTrigger>
          <TabsTrigger value="fulfilled">Fulfilled ({fulfilled.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="all">{prescriptionsTable(filtered, statusBadge)}</TabsContent>
        <TabsContent value="pending">{prescriptionsTable(filtered.filter((p) => p.status === 'prescribed' || p.status === 'ordered'), statusBadge)}</TabsContent>
        <TabsContent value="fulfilled">{prescriptionsTable(filtered.filter((p) => p.status === 'administered' || p.status === 'completed'), statusBadge)}</TabsContent>
      </Tabs>
    </div>
  );
}

function prescriptionsTable(list: Prescription[], badge: (s: string) => JSX.Element) {
  if (list.length === 0) {
    return <Card><CardContent className="text-center py-8 text-muted-foreground"><Pill className="h-8 w-8 mx-auto mb-2 opacity-50" /><p>No prescriptions found</p></CardContent></Card>;
  }
  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Medication</TableHead>
              <TableHead>Patient</TableHead>
              <TableHead>Dosage</TableHead>
              <TableHead>Frequency</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-medium">{p.medication_name}</TableCell>
                <TableCell>{p.patient_name || '-'}</TableCell>
                <TableCell>{p.dosage || '-'}</TableCell>
                <TableCell>{p.frequency || '-'}</TableCell>
                <TableCell>{badge(p.status)}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{p.prescribed_at ? formatDateTime(p.prescribed_at) : '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
