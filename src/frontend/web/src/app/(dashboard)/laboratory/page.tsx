'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { FlaskConical, Search, AlertTriangle, CheckCircle2, Clock, Plus, Loader2, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface Order {
  id: string; order_description: string; patient_name?: string; patient_id: string;
  status: string; interpretation?: string; ordered_datetime: string;
}

export default function LaboratoryPage() {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState('');
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((s) => s.accessToken);
  const role = useAuthStore(s => s.user?.role);
  const [error, setError] = useState('');

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/emr/orders?order_type=lab&per_page=100', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Unable to load laboratory requests. Please retry.');
      if (res.ok) {
        const data = await res.json();
        setOrders(data.items || data || []);
        setError('');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load requests');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchOrders(); }, [fetchOrders]);

  const filtered = orders.filter((o) =>
    (o.order_description || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (o.patient_name || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const pendingCount = orders.filter((o) => ['ordered', 'collected', 'received', 'in_progress'].includes(o.status)).length;
  const completedCount = orders.filter((o) => ['completed', 'resulted', 'verified'].includes(o.status)).length;
  const verifiedCount = orders.filter((o) => o.status === 'verified').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FlaskConical className="h-6 w-6 text-healthcare-blue" />
            Laboratory
          </h1>
          <p className="text-muted-foreground">Manage lab tests and results</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild><Link href="/laboratory/results"><CheckCircle2 className="h-4 w-4 mr-1" />View Results</Link></Button>
          {(role === 'provider' || role === 'admin') && <Button asChild><Link href="/laboratory/order"><Plus className="h-4 w-4 mr-1" />Order Test</Link></Button>}
        </div>
      </div>

      {error && <p role="alert" className="text-red-600">{error} <Button variant="outline" onClick={fetchOrders}>Retry</Button></p>}
      <p className="text-sm text-muted-foreground">Latest 100 lab requests. Open a request to collect a specimen, process a test or review results.</p>
      {loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <>
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
            {[
              { label: 'Total Orders', value: orders.length.toString(), icon: FlaskConical, color: 'text-blue-600 bg-blue-100' },
              { label: 'Pending', value: pendingCount.toString(), icon: Clock, color: 'text-amber-600 bg-amber-100' },
              { label: 'Completed', value: completedCount.toString(), icon: CheckCircle2, color: 'text-green-600 bg-green-100' },
              { label: 'Verified', value: verifiedCount.toString(), icon: CheckCircle2, color: 'text-green-600 bg-green-100' },
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
            <Input placeholder="Search orders..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-10" />
          </div>

          <Card>
            <CardContent className="p-0">
              {filtered.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FlaskConical className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No lab orders found</p>
                </div>
              ) : (
                <div className="divide-y">
                  {filtered.map((o) => (
                    <div key={o.id} className="flex items-center justify-between p-4 hover:bg-accent/50 cursor-pointer" onClick={() => router.push(`/laboratory/results/${o.id}`)}>
                      <div className="flex-1">
                        <p className="font-medium">{o.order_description || 'Lab Order'}</p>
                        <p className="text-xs text-muted-foreground mt-1">{o.patient_name || o.patient_id} · {new Date(o.ordered_datetime).toLocaleString()}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={o.interpretation === 'critical' ? 'destructive' : o.status === 'completed' ? 'success' : 'outline'}>
                          {o.status || o.interpretation || 'ordered'}
                        </Badge>
                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
