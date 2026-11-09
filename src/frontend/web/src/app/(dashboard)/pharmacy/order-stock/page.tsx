'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ShoppingCart, ArrowLeft, Package } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

export default function OrderStockPage() {
  const router = useRouter();
  const token = useAuthStore.getState().accessToken;
  const [supplierName, setSupplierName] = useState('');
  const [items, setItems] = useState<{ name: string; quantity: string; unit: string }[]>([{ name: '', quantity: '', unit: 'tabs' }]);
  const [deliveryDate, setDeliveryDate] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const addItem = () => setItems([...items, { name: '', quantity: '', unit: 'tabs' }]);
  const removeItem = (index: number) => setItems(items.filter((_, i) => i !== index));
  const updateItem = (index: number, field: 'name' | 'quantity' | 'unit', value: string) => {
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, [field]: value } : item)));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supplierName || items.some((i) => !i.name || !i.quantity)) {
      toast.error('Please fill in supplier name and all item details');
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch('/api/v1/emr/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          order_type: 'stock_order',
          description: `Stock order from ${supplierName}`,
          supplier: supplierName,
          items: items.map((i) => ({ name: i.name, quantity: parseInt(i.quantity), unit: i.unit })),
          delivery_date: deliveryDate || undefined,
          notes: notes || undefined,
        }),
      });
      if (res.ok) {
        toast.success('Stock order placed successfully');
        router.push('/pharmacy');
      } else {
        const data = await res.json();
        toast.error(data.detail || 'Failed to place order');
      }
    } catch {
      toast.error('Network error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const units = ['tabs', 'caps', 'ml', 'mg', 'sachets', 'vials', 'ampoules', 'units'];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/pharmacy"><ArrowLeft className="h-4 w-4 mr-1" />Back</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <ShoppingCart className="h-6 w-6 text-healthcare-blue" />
            Order Stock
          </h1>
          <p className="text-muted-foreground">Place a stock order with a supplier</p>
        </div>
      </div>

      <Card className="max-w-3xl">
        <CardHeader><CardTitle>Purchase Order Details</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Supplier Name *</label>
                <Input placeholder="e.g. PharmaCo Zambia" value={supplierName} onChange={(e) => setSupplierName(e.target.value)} required />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Expected Delivery Date</label>
                <Input type="date" value={deliveryDate} onChange={(e) => setDeliveryDate(e.target.value)} />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium">Order Items *</label>
                <Button type="button" variant="outline" size="sm" onClick={addItem}>
                  <Package className="h-3 w-3 mr-1" />Add Item
                </Button>
              </div>
              <div className="space-y-3">
                {items.map((item, idx) => (
                  <div key={idx} className="flex gap-2 items-start">
                    <div className="flex-1">
                      <Input placeholder="Medication name" value={item.name} onChange={(e) => updateItem(idx, 'name', e.target.value)} />
                    </div>
                    <div className="w-24">
                      <Input type="number" min="0" placeholder="Qty" value={item.quantity} onChange={(e) => updateItem(idx, 'quantity', e.target.value)} />
                    </div>
                    <select
                      value={item.unit}
                      onChange={(e) => updateItem(idx, 'unit', e.target.value)}
                      className="w-24 h-10 rounded-md border border-input bg-background px-2 text-sm"
                    >
                      {units.map((u) => (<option key={u} value={u}>{u}</option>))}
                    </select>
                    {items.length > 1 && (
                      <Button type="button" variant="ghost" size="icon" onClick={() => removeItem(idx)} className="text-red-500 h-10 w-10">
                        &times;
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Order Notes</label>
              <Textarea placeholder="Additional instructions or notes for the supplier..." value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="submit" className="bg-healthcare-green hover:bg-healthcare-green-dark" disabled={submitting}>
                {submitting ? 'Placing Order...' : 'Place Order'}
              </Button>
              <Button type="button" variant="outline" asChild>
                <Link href="/pharmacy">Cancel</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
