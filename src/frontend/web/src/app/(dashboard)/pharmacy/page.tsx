'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Pill, Search, ShoppingCart, Package, AlertTriangle, TrendingDown, Plus, Loader2, Clock, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';

interface Prescription {
  id: string; medication_name: string; patient_name?: string;
  dosage?: string; status: string; prescribed_at?: string;
}

export default function PharmacyDashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const token = useAuthStore((s) => s.accessToken);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/emr/orders?order_type=prescription&per_page=50', {
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
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const filtered = prescriptions.filter((p) => {
    const q = searchTerm.toLowerCase();
    return (p.medication_name || '').toLowerCase().includes(q) || (p.patient_name || '').toLowerCase().includes(q);
  });

  const pending = prescriptions.filter((p) => p.status === 'prescribed' || p.status === 'ordered');
  const fulfilled = prescriptions.filter((p) => p.status === 'administered' || p.status === 'completed');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Pill className="h-6 w-6 text-green-600" />
            Pharmacy
          </h1>
          <p className="text-muted-foreground">Medication management and order fulfillment</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild><Link href="/pharmacy/add-medication"><Plus className="h-4 w-4 mr-1" />Add Medication</Link></Button>
          <Button variant="outline" asChild><Link href="/pharmacy/order-stock"><ShoppingCart className="h-4 w-4 mr-1" />Order Stock</Link></Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <>
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
            {[
              { label: 'Total Prescriptions', value: prescriptions.length.toString(), icon: Pill, color: 'text-blue-600 bg-blue-100' },
              { label: 'Pending Fulfillment', value: pending.length.toString(), icon: Clock, color: 'text-amber-600 bg-amber-100' },
              { label: 'Fulfilled', value: fulfilled.length.toString(), icon: CheckCircle2, color: 'text-green-600 bg-green-100' },
              { label: 'Low Stock Items', value: '0', icon: AlertTriangle, color: 'text-red-600 bg-red-100' },
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
            <TabsContent value="all">
              <Card>
                <CardContent className="p-4">
                  {filtered.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">No prescriptions found</p>
                  ) : (
                    <div className="space-y-2">
                      {filtered.map((p) => (
                        <div key={p.id} className="flex items-center justify-between p-3 rounded-lg border">
                          <div>
                            <p className="font-medium">{p.medication_name}</p>
                            <p className="text-xs text-muted-foreground">{p.patient_name || 'N/A'} - {p.dosage || ''}</p>
                          </div>
                          <Badge variant={p.status === 'administered' || p.status === 'completed' ? 'success' : 'outline'}>{p.status}</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="pending">
              <Card><CardContent className="p-4">
                {pending.length === 0 ? <p className="text-center text-muted-foreground py-8">No pending prescriptions</p> : (
                  <div className="space-y-2">{pending.map((p) => (
                    <div key={p.id} className="flex items-center justify-between p-3 rounded-lg border">
                      <div><p className="font-medium">{p.medication_name}</p><p className="text-xs text-muted-foreground">{p.patient_name}</p></div>
                      <Badge variant="outline">{p.status}</Badge>
                    </div>
                  ))}</div>
                )}
              </CardContent></Card>
            </TabsContent>
            <TabsContent value="fulfilled">
              <Card><CardContent className="p-4">
                {fulfilled.length === 0 ? <p className="text-center text-muted-foreground py-8">No fulfilled prescriptions</p> : (
                  <div className="space-y-2">{fulfilled.map((p) => (
                    <div key={p.id} className="flex items-center justify-between p-3 rounded-lg border">
                      <div><p className="font-medium">{p.medication_name}</p><p className="text-xs text-muted-foreground">{p.patient_name}</p></div>
                      <Badge variant="success">fulfilled</Badge>
                    </div>
                  ))}</div>
                )}
              </CardContent></Card>
            </TabsContent>
          </Tabs>

          <div className="grid gap-4 grid-cols-2">
            <Button asChild variant="outline" className="h-20"><Link href="/pharmacy/prescriptions"><Pill className="h-5 w-5 mr-2" />View All Prescriptions</Link></Button>
            <Button asChild variant="outline" className="h-20"><Link href="/pharmacy/inventory"><Package className="h-5 w-5 mr-2" />View Inventory</Link></Button>
          </div>
        </>
      )}
    </div>
  );
}
