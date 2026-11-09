'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Pill, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

export default function AddMedicationPage() {
  const router = useRouter();
  const token = useAuthStore.getState().accessToken;
  const [medicationName, setMedicationName] = useState('');
  const [genericName, setGenericName] = useState('');
  const [category, setCategory] = useState('');
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('tabs');
  const [reorderLevel, setReorderLevel] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [supplier, setSupplier] = useState('');
  const [costPrice, setCostPrice] = useState('');
  const [sellingPrice, setSellingPrice] = useState('');
  const [batchNumber, setBatchNumber] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!medicationName || !quantity) {
      toast.error('Please fill in medication name and quantity');
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch('/api/v1/emr/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          order_type: 'medication',
          medication_name: medicationName,
          generic_name: genericName || undefined,
          category: category || undefined,
          quantity: parseInt(quantity),
          unit,
          reorder_level: reorderLevel ? parseInt(reorderLevel) : undefined,
          expiry_date: expiryDate || undefined,
          supplier: supplier || undefined,
          cost_price: costPrice ? parseFloat(costPrice) : undefined,
          selling_price: sellingPrice ? parseFloat(sellingPrice) : undefined,
          batch_number: batchNumber || undefined,
        }),
      });
      if (res.ok) {
        toast.success('Medication added to inventory');
        router.push('/pharmacy');
      } else {
        const data = await res.json();
        toast.error(data.detail || 'Failed to add medication');
      }
    } catch {
      toast.error('Network error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const categories = ['Antimalarial', 'Antidiabetic', 'Antihypertensive', 'Antibiotic', 'GI', 'Pain Management', 'Respiratory', 'Nutritional', 'Vaccine', 'Other'];

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
            <Pill className="h-6 w-6 text-healthcare-blue" />
            Add Medication
          </h1>
          <p className="text-muted-foreground">Add a new medication to pharmacy inventory</p>
        </div>
      </div>

      <Card className="max-w-3xl">
        <CardHeader><CardTitle>Medication Details</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Medication Name *</label>
                <Input placeholder="e.g. Artemether-Lumefantrine" value={medicationName} onChange={(e) => setMedicationName(e.target.value)} required />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Generic Name</label>
                <Input placeholder="e.g. Coartem" value={genericName} onChange={(e) => setGenericName(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Category</label>
              <div className="flex flex-wrap gap-2">
                {categories.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setCategory(c)}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${category === c ? 'bg-healthcare-green/10 border-healthcare-green text-healthcare-green' : 'bg-background hover:bg-accent'}`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Quantity *</label>
                <Input type="number" min="0" placeholder="0" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Unit</label>
                <select value={unit} onChange={(e) => setUnit(e.target.value)} className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm">
                  {['tabs', 'caps', 'ml', 'mg', 'sachets', 'vials', 'ampoules', 'units'].map((u) => (
                    <option key={u} value={u}>{u}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Reorder Level</label>
                <Input type="number" min="0" placeholder="0" value={reorderLevel} onChange={(e) => setReorderLevel(e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Batch Number</label>
                <Input placeholder="e.g. AL-2024-001" value={batchNumber} onChange={(e) => setBatchNumber(e.target.value)} />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Expiry Date</label>
                <Input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Cost Price (ZMW)</label>
                <Input type="number" step="0.01" min="0" placeholder="0.00" value={costPrice} onChange={(e) => setCostPrice(e.target.value)} />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Selling Price (ZMW)</label>
                <Input type="number" step="0.01" min="0" placeholder="0.00" value={sellingPrice} onChange={(e) => setSellingPrice(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Supplier</label>
              <Input placeholder="e.g. PharmaCo Zambia" value={supplier} onChange={(e) => setSupplier(e.target.value)} />
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="submit" className="bg-healthcare-green hover:bg-healthcare-green-dark" disabled={submitting}>
                {submitting ? 'Adding...' : 'Add Medication'}
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
