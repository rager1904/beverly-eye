'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { FlaskConical, Search, AlertTriangle, CheckCircle2, Clock, ArrowLeft, Loader2, Eye } from 'lucide-react';
import Link from 'next/link';
import { formatDateTime } from '@/lib/utils';
import { clinicalApi } from '@/lib/clinical-api';

interface LabResult {
  id: string;
  order_id?: string;
  order_code?: string;
  order_description: string;
  result_type: string;
  result_value: string;
  result_unit: string;
  reference_range_low: string;
  reference_range_high: string;
  interpretation: string;
  status: string;
  patient_name?: string;
  patient_id?: string;
  ordered_by: string;
  ordered_datetime: string;
  performed_datetime: string;
  result_datetime: string;
}

export default function LabResultsPage() {
  const router = useRouter();
  const [results, setResults] = useState<LabResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState('');

  const fetchResults = useCallback(async () => {
    setLoading(true);
    try {
      const pages = await Promise.all(['resulted', 'verified'].map(status =>
        clinicalApi<{ items: LabResult[] }>(`emr/orders?order_type=lab&status=${status}&per_page=20`)));
      const rows = await Promise.all(pages.flatMap(page => page.items).map(async order => {
        const values = await clinicalApi<LabResult[]>(`emr/orders/${order.id}/results`);
        return values.map(result => ({ ...result, order_id: order.id, status: order.status, order_description: order.order_description }));
      }));
      setResults(rows.flat());
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load results');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchResults(); }, [fetchResults]);

  const filtered = results.filter((r) =>
    (r.order_description || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (r.patient_name || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const pendingCount = results.filter((r) => r.status === 'resulted').length;
  const criticalCount = results.filter((r) => r.interpretation === 'critical').length;
  const completedCount = results.filter((r) => r.status === 'verified').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/laboratory"><ArrowLeft className="h-4 w-4 mr-1" />Back to Lab</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <FlaskConical className="h-6 w-6 text-healthcare-blue" />
            Lab Results
          </h1>
          <p className="text-muted-foreground">Results from the latest 20 requests in each verification state</p>
        </div>
      </div>

      {error && <p role="alert" className="text-red-600">{error} <Button variant="outline" onClick={fetchResults}>Retry</Button></p>}
      {loading && <p role="status">Loading results…</p>}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Total Results', value: results.length.toString(), icon: FlaskConical, color: 'text-blue-600 bg-blue-100' },
          { label: 'Awaiting verification', value: pendingCount.toString(), icon: Clock, color: 'text-amber-600 bg-amber-100' },
          { label: 'Critical', value: criticalCount.toString(), icon: AlertTriangle, color: 'text-red-600 bg-red-100' },
          { label: 'Verified', value: completedCount.toString(), icon: CheckCircle2, color: 'text-green-600 bg-green-100' },
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
        <Input placeholder="Search results..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-10 h-12 text-base" />
      </div>

      <Tabs defaultValue="all">
        <TabsList>
          <TabsTrigger value="all">All ({results.length})</TabsTrigger>
          <TabsTrigger value="pending">Pending ({pendingCount})</TabsTrigger>
          <TabsTrigger value="critical">Critical ({criticalCount})</TabsTrigger>
        </TabsList>

        <TabsContent value="all">
          {renderTable(filtered, router)}
        </TabsContent>
        <TabsContent value="pending">
          {renderTable(filtered.filter((r) => r.status === 'resulted'), router)}
        </TabsContent>
        <TabsContent value="critical">
          {renderTable(filtered.filter((r) => r.interpretation === 'critical'), router)}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function renderTable(results: LabResult[], router: any) {
  if (results.length === 0) {
    return (
      <Card><CardContent className="text-center py-8 text-muted-foreground">
        <FlaskConical className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>No results found</p>
      </CardContent></Card>
    );
  }
  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Patient</TableHead>
              <TableHead>Test</TableHead>
              <TableHead>Result</TableHead>
              <TableHead>Reference</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="w-16"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((r) => (
              <TableRow key={r.id} className="cursor-pointer hover:bg-accent/50" onClick={() => router.push(`/laboratory/results/${r.order_id}`)}>
                <TableCell className="font-medium">{r.patient_name || r.patient_id}</TableCell>
                <TableCell>{r.order_description || r.result_type}</TableCell>
                <TableCell>
                  <span className={r.interpretation === 'critical' ? 'text-red-600 font-bold' : r.interpretation === 'abnormal' ? 'text-amber-600' : ''}>
                    {r.result_value || '-'}
                  </span>
                  {r.result_unit && <span className="text-xs text-muted-foreground ml-1">{r.result_unit}</span>}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {r.reference_range_low && r.reference_range_high ? `${r.reference_range_low} - ${r.reference_range_high}` : '-'}
                </TableCell>
                <TableCell>
                  <Badge variant={r.interpretation === 'critical' ? 'destructive' : r.status === 'completed' ? 'success' : 'outline'}>
                    {r.status || r.interpretation}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">{r.result_datetime ? formatDateTime(r.result_datetime) : '-'}</TableCell>
                <TableCell>
                  <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); router.push(`/laboratory/results/${r.order_id}`); }}>
                    <Eye className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
