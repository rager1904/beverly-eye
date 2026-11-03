'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Pill, AlertTriangle, Clock } from 'lucide-react';
import type { PharmacyStock } from '@/types';

interface PharmacyStockProps {
  items: PharmacyStock[];
  isLoading?: boolean;
}

export function PharmacyStock({ items, isLoading }: PharmacyStockProps) {
  const lowStock = items.filter((i) => i.quantity <= i.reorder_level);
  const expiringSoon = items.filter((i) => {
    const daysUntilExpiry = Math.ceil((new Date(i.expiry_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    return daysUntilExpiry <= 30 && daysUntilExpiry > 0;
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Pill className="h-5 w-5" />Pharmacy Stock</CardTitle></CardHeader>
        <CardContent><div className="space-y-3">{Array.from({ length: 4 }).map((_, i) => (<div key={i} className="h-14 bg-muted animate-pulse rounded-lg" />))}</div></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Pill className="h-5 w-5 text-healthcare-blue" />
          Pharmacy Alerts
        </CardTitle>
        <div className="flex gap-2">
          {lowStock.length > 0 && <Badge variant="warning">{lowStock.length} low</Badge>}
          {expiringSoon.length > 0 && <Badge variant="critical">{expiringSoon.length} expiring</Badge>}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {lowStock.length === 0 && expiringSoon.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">All stock levels normal</p>
          ) : (
            <>
              {lowStock.map((item) => (
                <div key={item.id} className="flex items-center justify-between p-3 rounded-lg border border-amber-200 bg-amber-50/50">
                  <div>
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                      <span className="font-medium">{item.medication_name}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">Stock: {item.quantity} {item.unit} (Reorder at: {item.reorder_level})</p>
                  </div>
                  <Badge variant="warning">Low Stock</Badge>
                </div>
              ))}
              {expiringSoon.map((item) => {
                const daysLeft = Math.ceil((new Date(item.expiry_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
                return (
                  <div key={`exp-${item.id}`} className="flex items-center justify-between p-3 rounded-lg border border-red-200 bg-red-50/50">
                    <div>
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-red-500" />
                        <span className="font-medium">{item.medication_name}</span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">Batch: {item.batch_number} - Expires in {daysLeft} days</p>
                    </div>
                    <Badge variant="critical">{daysLeft}d</Badge>
                  </div>
                );
              })}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
