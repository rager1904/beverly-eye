'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { BedOccupancy } from '@/components/dashboard/BedOccupancy';
import { DiseaseAlerts } from '@/components/dashboard/DiseaseAlerts';
import { Building2, TrendingUp, AlertTriangle, Users, Shield, MapPin, Activity, Loader2 } from 'lucide-react';
import { AiChatWidget } from '@/components/patient/AiChatWidget';
import Link from 'next/link';

interface AlertItem {
  id: string; disease: string; district: string; province: string;
  cases_reported: number; severity: string; status: string; reported_at: string; notes?: string;
}

export default function HospitalAdminPage() {
  const [chatOpen, setChatOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [dashboard, setDashboard] = useState<any>(null);
  const token = useAuthStore((s) => s.accessToken);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [dashRes, alertsRes] = await Promise.all([
        fetch('/api/v1/public-health/dashboard', { headers }),
        fetch('/api/v1/public-health/alerts?limit=10', { headers }),
      ]);
      if (dashRes.ok) setDashboard(await dashRes.json());
      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlerts(data.alerts || []);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Building2 className="h-6 w-6 text-healthcare-blue" />
            Hospital Administration
          </h1>
            <p className="text-muted-foreground">Eye &amp; Dental Hospital - Lusaka, Zambia</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <>
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-5">
            {[
              { label: 'Active Outbreaks', value: (dashboard?.active_outbreaks ?? alerts.length).toString(), icon: AlertTriangle, color: 'text-red-600 bg-red-100' },
              { label: 'Cases This Week', value: (dashboard?.weekly_cases ?? 0).toLocaleString(), icon: TrendingUp, color: 'text-blue-600 bg-blue-100' },
              { label: 'Total Cases', value: (dashboard?.total_cases ?? 0).toLocaleString(), icon: Users, color: 'text-green-600 bg-green-100' },
              { label: 'Districts', value: (dashboard?.districts_monitored ?? 0).toString(), icon: MapPin, color: 'text-purple-600 bg-purple-100' },
              { label: 'Vaccination Rate', value: `${dashboard?.vaccination_rate ?? 0}%`, icon: Shield, color: 'text-amber-600 bg-amber-100' },
            ].map(({ label, value, icon: Icon, color }) => (
              <Card key={label}>
                <CardContent className="p-3 text-center">
                  <div className={`w-10 h-10 rounded-full ${color} flex items-center justify-center mx-auto mb-2`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <p className="text-xl font-bold">{value}</p>
                  <p className="text-xs text-muted-foreground">{label}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-6">
              <BedOccupancy data={[]} />
              <DiseaseAlerts alerts={alerts as any} />
            </div>
            <div className="space-y-6">
              <Card>
                <CardHeader><CardTitle className="text-lg">Quick Actions</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  <Button className="w-full justify-start" variant="outline" asChild><Link href="/hospital/admit">Admit patient</Link></Button>
                  <Button className="w-full justify-start" variant="outline" asChild>
                    <Link href="/public-health"><Activity className="h-4 w-4 mr-2" />Public Health Dashboard</Link>
                  </Button>
                  <Button className="w-full justify-start" variant="outline" asChild>
                    <Link href="/public-health/report-outbreak"><AlertTriangle className="h-4 w-4 mr-2" />Report Outbreak</Link>
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}
      <AiChatWidget open={chatOpen} onOpenChange={setChatOpen} />
    </div>
  );
}
