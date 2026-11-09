'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Syringe, ArrowLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';

interface CoverageItem {
  district: string;
  immunized: number;
  total: number;
  coverage: number;
}

export default function VaccinationCampaignsPage() {
  const [coverage, setCoverage] = useState<CoverageItem[]>([]);
  const [loading, setLoading] = useState(true);

  const token = useAuthStore((s) => s.accessToken);

  const fetchCoverage = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/public-health/vaccination-coverage', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCoverage(data.coverage || []);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCoverage();
  }, [fetchCoverage]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/public-health"><ArrowLeft className="h-4 w-4 mr-1" />Back</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <Syringe className="h-6 w-6 text-purple-600" />
            Vaccination Campaigns
          </h1>
          <p className="text-muted-foreground">Vaccination coverage and immunization campaigns</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : coverage.length === 0 ? (
        <Card>
          <CardContent className="text-center py-8 text-muted-foreground">
            <Syringe className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No vaccination data available</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
            {[
              { label: 'Districts with Data', value: coverage.length.toString() },
              { label: 'Average Coverage', value: `${Math.round(coverage.reduce((s, c) => s + c.coverage, 0) / coverage.length)}%` },
              { label: 'Total Immunized', value: coverage.reduce((s, c) => s + c.immunized, 0).toLocaleString() },
              { label: 'Total Population', value: coverage.reduce((s, c) => s + c.total, 0).toLocaleString() },
            ].map(({ label, value }) => (
              <Card key={label}>
                <CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold">{value}</p>
                  <p className="text-xs text-muted-foreground">{label}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader><CardTitle className="text-lg">Coverage by District</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={coverage}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="district" />
                  <YAxis domain={[0, 100]} unit="%" />
                  <Tooltip formatter={(value: number) => `${value}%`} />
                  <Bar dataKey="coverage" fill="#22c55e" name="Coverage" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-lg">Detailed Coverage by District</CardTitle></CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">District</th>
                      <th className="text-right p-2">Immunized</th>
                      <th className="text-right p-2">Total Population</th>
                      <th className="text-right p-2">Coverage</th>
                      <th className="text-right p-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {coverage.map((c) => (
                      <tr key={c.district} className="border-b hover:bg-accent/50">
                        <td className="p-2 font-medium">{c.district}</td>
                        <td className="p-2 text-right">{c.immunized.toLocaleString()}</td>
                        <td className="p-2 text-right">{c.total.toLocaleString()}</td>
                        <td className="p-2 text-right">{c.coverage}%</td>
                        <td className="p-2 text-right">
                          <Badge variant={c.coverage >= 80 ? 'success' : c.coverage >= 60 ? 'warning' : 'destructive'}>
                            {c.coverage >= 80 ? 'On Target' : c.coverage >= 60 ? 'Needs Improvement' : 'Critical'}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
