'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Activity, ArrowLeft, Loader2, MapPin, Search } from 'lucide-react';
import Link from 'next/link';

interface DiseaseCase {
  id: string;
  disease: string;
  status: string;
  severity: string;
  district: string;
  province: string;
  facility_name: string | null;
  patient_age: number | null;
  patient_gender: string | null;
  diagnosis_date: string;
  outcome: string | null;
}

export default function DiseaseCasesPage() {
  const [cases, setCases] = useState<DiseaseCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchDisease, setSearchDisease] = useState('');
  const [searchDistrict, setSearchDistrict] = useState('');

  const fetchCases = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchDisease) params.set('disease', searchDisease);
      if (searchDistrict) params.set('district', searchDistrict);
      params.set('limit', '100');
      const token = useAuthStore.getState().accessToken;
      const res = await fetch(`/api/v1/public-health/cases?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCases(data.cases || []);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [searchDisease, searchDistrict]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const severityColor = (s: string) => {
    switch (s) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'severe': return 'bg-orange-100 text-orange-800';
      case 'moderate': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/public-health"><ArrowLeft className="h-4 w-4 mr-1" />Back</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <Activity className="h-6 w-6 text-healthcare-blue" />
            Disease Cases
          </h1>
          <p className="text-muted-foreground">View and search reported disease cases</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Search className="h-5 w-5" />Search Cases
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="Filter by district..."
              value={searchDistrict}
              onChange={(e) => setSearchDistrict(e.target.value)}
              className="max-w-xs"
            />
            <Select value={searchDisease} onValueChange={setSearchDisease}>
              <SelectTrigger className="max-w-xs">
                <SelectValue placeholder="All diseases" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All diseases</SelectItem>
                <SelectItem value="Malaria">Malaria</SelectItem>
                <SelectItem value="Cholera">Cholera</SelectItem>
                <SelectItem value="HIV/AIDS">HIV/AIDS</SelectItem>
                <SelectItem value="Measles">Measles</SelectItem>
                <SelectItem value="Tuberculosis">Tuberculosis</SelectItem>
                <SelectItem value="COVID-19">COVID-19</SelectItem>
                <SelectItem value="Typhoid">Typhoid</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={fetchCases}><Search className="h-4 w-4 mr-2" />Search</Button>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : cases.length === 0 ? (
        <Card>
          <CardContent className="text-center py-8 text-muted-foreground">
            <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No disease cases found</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Reported Cases ({cases.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {cases.map((c) => (
                <div key={c.id} className="p-3 rounded-lg border hover:bg-accent/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{c.disease}</span>
                      <Badge variant="outline" className={severityColor(c.severity)}>{c.severity}</Badge>
                      <Badge variant={c.status === 'confirmed' ? 'destructive' : 'outline'}>{c.status}</Badge>
                    </div>
                    {c.outcome && <Badge variant={c.outcome === 'dead' ? 'destructive' : 'secondary'}>{c.outcome}</Badge>}
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{c.district}, {c.province}</span>
                    {c.facility_name && <span>{c.facility_name}</span>}
                    <span>{c.diagnosis_date}</span>
                    {c.patient_age && <span>Age: {c.patient_age}</span>}
                    {c.patient_gender && <span>{c.patient_gender}</span>}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
