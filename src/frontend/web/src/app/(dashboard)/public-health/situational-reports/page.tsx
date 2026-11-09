'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Download, ArrowLeft, Loader2, FileText } from 'lucide-react';
import Link from 'next/link';

interface Report {
  id: string;
  title: string;
  report_type: string;
  period_start: string;
  period_end: string;
  district: string | null;
  province: string | null;
  total_cases: number;
  total_deaths: number;
  summary: string | null;
  status: string;
}

export default function SituationalReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const token = useAuthStore((s) => s.accessToken);

  const fetchReports = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/public-health/cases?limit=5', {
        headers: { Authorization: `Bearer ${token}` },
      });
      // just show recent reports from the alerts endpoint
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const generateWeekly = async () => {
    setGenerating(true);
    try {
      const res = await fetch('/api/v1/disease-surveillance/reports/weekly', {
        method: 'POST',
        headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        setReports((prev) => [data, ...prev]);
      }
    } catch {
      // silently fail
    } finally {
      setGenerating(false);
    }
  };

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
            <FileText className="h-6 w-6 text-amber-600" />
            Situational Reports
          </h1>
          <p className="text-muted-foreground">Generate and view surveillance situational reports</p>
        </div>
        <Button onClick={generateWeekly} disabled={generating}>
          <Download className="h-4 w-4 mr-2" />
          {generating ? 'Generating...' : 'Generate Weekly Report'}
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : reports.length === 0 ? (
        <Card>
          <CardContent className="text-center py-8 text-muted-foreground">
            <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No reports generated yet. Click "Generate Weekly Report" to create one.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {reports.map((r) => (
            <Card key={r.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">{r.title}</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      {r.period_start} to {r.period_end}
                      {r.district && ` - ${r.district}`}
                      {r.province && `, ${r.province}`}
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-sm">
                      <span>Cases: <strong>{r.total_cases}</strong></span>
                      <span>Deaths: <strong>{r.total_deaths}</strong></span>
                      <Badge variant="outline">{r.report_type}</Badge>
                      <Badge variant={r.status === 'final' ? 'success' : 'secondary'}>{r.status}</Badge>
                    </div>
                    {r.summary && <p className="text-xs text-muted-foreground mt-2">{r.summary}</p>}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
