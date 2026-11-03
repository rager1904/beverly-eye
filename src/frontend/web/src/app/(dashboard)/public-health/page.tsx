'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DiseaseAlerts } from '@/components/dashboard/DiseaseAlerts';
import { AiChatWidget } from '@/components/patient/AiChatWidget';
import { MapPin, Activity, AlertTriangle, Shield, Syringe, Users, Thermometer, Download, RefreshCw, Loader2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';
import type { DiseaseAlert } from '@/types';

interface DashboardData {
  weekly_cases: number;
  monthly_cases: number;
  total_cases: number;
  total_deaths: number;
  active_outbreaks: number;
  districts_monitored: number;
  vaccination_rate: number;
  health_facilities: number;
}

interface AlertItem {
  id: string;
  disease: string;
  district: string;
  province: string;
  cases_reported: number;
  severity: 'low' | 'moderate' | 'high' | 'critical';
  status: 'active' | 'investigating' | 'contained';
  reported_at: string;
  deaths?: number;
  notes?: string;
}

interface TrendItem {
  week: string;
  [key: string]: string | number;
}

interface CoverageItem {
  district: string;
  immunized: number;
  total: number;
  coverage: number;
}

interface DistrictProfile {
  district: string;
  patients: number;
  encounters: number;
  facilities: number;
  doctors: number;
  beds: number;
  visits: number;
}

export default function PublicHealthPage() {
  const router = useRouter();
  const [chatOpen, setChatOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [alertsData, setAlertsData] = useState<AlertItem[]>([]);
  const [trendsData, setTrendsData] = useState<TrendItem[]>([]);
  const [coverageData, setCoverageData] = useState<CoverageItem[]>([]);
  const [districtData, setDistrictData] = useState<DistrictProfile[]>([]);

  const token = useAuthStore((s) => s.accessToken);
  const apiBase = '/api/v1/public-health';
  const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = { ...authHeaders };
      const [dashRes, alertsRes, trendsRes, coverageRes, districtRes] = await Promise.all([
        fetch(`${apiBase}/dashboard`, { headers }),
        fetch(`${apiBase}/alerts?limit=10`, { headers }),
        fetch(`${apiBase}/trends?weeks=8`, { headers }),
        fetch(`${apiBase}/vaccination-coverage`, { headers }),
        fetch(`${apiBase}/district-health`, { headers }),
      ]);

      if (dashRes.ok) setDashboard(await dashRes.json());
      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlertsData(data.alerts || []);
      }
      if (trendsRes.ok) {
        const data = await trendsRes.json();
        setTrendsData(data.trends || []);
      }
      if (coverageRes.ok) {
        const data = await coverageRes.json();
        setCoverageData(data.coverage || []);
      }
      if (districtRes.ok) {
        const data = await districtRes.json();
        setDistrictData(data.districts || []);
      }
    } catch (e) {
      setError('Failed to load public health data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const criticalAlerts = alertsData.filter(
    (a) => a.severity === 'critical' || a.severity === 'high'
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Activity className="h-6 w-6 text-healthcare-blue" />
            Public Health Surveillance
          </h1>
          <p className="text-muted-foreground">Zambia National Public Health Institute - Disease Monitoring</p>
        </div>
        <div className="flex gap-2">
          {error && <p className="text-sm text-red-500">{error}</p>}
          <Badge variant="critical" className="flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            {dashboard?.active_outbreaks ?? 0} Active Alerts
          </Badge>
          <Button variant="outline" size="icon" onClick={fetchAll} title="Refresh data">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button variant="outline"><Download className="h-4 w-4 mr-1" />Export Report</Button>
        </div>
      </div>

      <div className="grid gap-4 grid-cols-2 lg:grid-cols-5">
        {[
          { label: 'Reported Cases (This Week)', value: (dashboard?.weekly_cases ?? 0).toLocaleString(), icon: Thermometer, color: 'text-red-600 bg-red-100' },
          { label: 'Districts Monitored', value: (dashboard?.districts_monitored ?? 0).toLocaleString(), icon: MapPin, color: 'text-blue-600 bg-blue-100' },
          { label: 'Active Surveillance', value: (dashboard?.active_outbreaks ?? 0).toLocaleString(), icon: Shield, color: 'text-green-600 bg-green-100' },
          { label: 'Vaccination Rate', value: `${dashboard?.vaccination_rate ?? 0}%`, icon: Syringe, color: 'text-purple-600 bg-purple-100' },
          { label: 'Health Facilities', value: (dashboard?.health_facilities ?? 0).toLocaleString(), icon: Users, color: 'text-amber-600 bg-amber-100' },
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
          <DiseaseAlerts alerts={alertsData as DiseaseAlert[]} />

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Weekly Disease Trends</CardTitle>
            </CardHeader>
            <CardContent>
              {trendsData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={trendsData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="week" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    {Object.keys(trendsData[0] || {})
                      .filter((k) => k !== 'week')
                      .map((disease, i) => {
                        const colors = ['#ef4444', '#f59e0b', '#0ea5e9', '#8b5cf6', '#22c55e', '#ec4899'];
                        return (
                          <Line
                            key={disease}
                            type="monotone"
                            dataKey={disease}
                            stroke={colors[i % colors.length]}
                            strokeWidth={2}
                            name={disease.charAt(0).toUpperCase() + disease.slice(1).replace('_', '/')}
                            connectNulls
                          />
                        );
                      })}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No trend data available</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-lg">Vaccination Coverage by District</CardTitle></CardHeader>
            <CardContent>
              {coverageData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={coverageData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="district" />
                    <YAxis domain={[0, 100]} unit="%" />
                    <Tooltip formatter={(value: number) => `${value}%`} />
                    <Bar dataKey="coverage" fill="#22c55e" name="Coverage" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No vaccination data available</p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle className="text-lg flex items-center gap-2"><MapPin className="h-5 w-5" />District Health Profile</CardTitle></CardHeader>
            <CardContent>
              {districtData.length > 0 ? (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {districtData.map((d) => (
                    <div key={d.district} className="p-3 rounded-lg border hover:bg-accent/50 transition-colors">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{d.district}</span>
                        <Badge variant="outline">{d.facilities || '?'} facilities</Badge>
                      </div>
                      <div className="grid grid-cols-3 gap-2 mt-2 text-xs text-muted-foreground">
                        <span>{d.doctors || '?'} doctors</span>
                        <span>{d.beds || '?'} beds</span>
                        <span>{(d.visits || 0).toLocaleString()} visits</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No district data available</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-lg">Quick Actions</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              <Button className="w-full justify-start" variant="outline" onClick={() => router.push('/public-health/report-outbreak')}>
                <AlertTriangle className="h-4 w-4 mr-2" />Report Outbreak
              </Button>
              <Button className="w-full justify-start" variant="outline" onClick={() => router.push('/public-health/disease-cases')}>
                <Shield className="h-4 w-4 mr-2" />Deploy Response Team
              </Button>
              <Button className="w-full justify-start" variant="outline" onClick={() => router.push('/public-health/vaccination-campaigns')}>
                <Syringe className="h-4 w-4 mr-2" />Vaccination Campaign
              </Button>
              <Button className="w-full justify-start" variant="outline" onClick={() => router.push('/public-health/situational-reports')}>
                <Download className="h-4 w-4 mr-2" />Generate Situational Report
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
      <AiChatWidget open={chatOpen} onOpenChange={setChatOpen} />
    </div>
  );
}
