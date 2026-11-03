'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Package, Search, ArrowLeft, AlertTriangle, Plus, Loader2 } from 'lucide-react';
import Link from 'next/link';

interface InventoryItem {
  id: string; medication_name: string; category?: string;
  quantity: number; unit?: string; expiry_date?: string;
}

export default function InventoryPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((s) => s.accessToken);

  const fetchInventory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/emr/orders?per_page=50', {
        headers: { Authorization: `Bearer ${token}` },
      });
      // Use medications as inventory proxy if no dedicated endpoint
      if (res.ok) {
        const data = await res.json();
        const items = data.items || data || [];
        setInventory(items.map((i: any) => ({
          id: i.id,
          medication_name: i.medication_name || i.order_description || 'Item',
          category: i.order_type || i.result_type,
          quantity: 0,
          unit: i.result_unit || 'units',
        })));
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchInventory(); }, [fetchInventory]);

  const filtered = inventory.filter((i) =>
    (i.medication_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (i.category || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild><Link href="/pharmacy"><ArrowLeft className="h-4 w-4 mr-1" />Back to Pharmacy</Link></Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <Package className="h-6 w-6 text-healthcare-blue" />Inventory
          </h1>
          <p className="text-muted-foreground">Track medication stock levels</p>
        </div>
        <Button asChild><Link href="/pharmacy/add-medication"><Plus className="h-4 w-4 mr-2" />Add Item</Link></Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        <Input placeholder="Search inventory..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-10" />
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : filtered.length === 0 ? (
        <Card><CardContent className="text-center py-8 text-muted-foreground">
          <Package className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No inventory items found. Add medications or check your stock orders.</p>
        </CardContent></Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((item) => (
            <Card key={item.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{item.medication_name}</span>
                  {item.quantity <= 0 && <Badge variant="outline" className="bg-red-100 text-red-800">No Stock</Badge>}
                </div>
                <div className="mt-2 text-sm text-muted-foreground">
                  <p>Category: {item.category || 'General'}</p>
                  <p>Qty: {item.quantity} {item.unit || 'units'}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
