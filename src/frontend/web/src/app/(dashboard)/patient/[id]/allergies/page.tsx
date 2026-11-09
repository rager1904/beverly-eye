'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, ArrowLeft, Loader2, Plus } from 'lucide-react';
import Link from 'next/link';

interface Allergy {
  id: string;
  allergen: string;
  reaction?: string;
  severity: string;
  onset_date?: string;
  status: string;
  is_drug_allergy?: boolean;
}

export default function PatientAllergiesPage() {
  const params = useParams();
  const router = useRouter();
  const [allergies, setAllergies] = useState<Allergy[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAllergies = useCallback(async () => {
    setLoading(true);
    try {
      const token = useAuthStore.getState().accessToken;
      const res = await fetch(`/api/v1/emr/patients/${params.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAllergies((data.data?.allergies || data.allergies || []));
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => { fetchAllergies(); }, [fetchAllergies]);

  const severityColor = (s: string) => {
    switch (s) {
      case 'anaphylaxis': return 'bg-red-100 text-red-800';
      case 'severe': return 'bg-orange-100 text-orange-800';
      case 'moderate': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href={`/patient/${params.id}`}><ArrowLeft className="h-4 w-4 mr-1" />Back to Patient</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <AlertTriangle className="h-6 w-6 text-red-500" />
            Allergies
          </h1>
          <p className="text-muted-foreground">Patient allergies and adverse reactions</p>
        </div>
        <Button variant="outline"><Plus className="h-4 w-4 mr-2" />Add Allergy</Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : allergies.length === 0 ? (
        <Card><CardContent className="text-center py-8 text-muted-foreground">
          <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No allergies recorded for this patient</p>
        </CardContent></Card>
      ) : (
        <div className="space-y-3">
          {allergies.map((a) => (
            <Card key={a.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{a.allergen}</span>
                    {a.is_drug_allergy && <Badge variant="outline" className="text-red-600 border-red-300">Drug Allergy</Badge>}
                    <Badge variant="outline" className={severityColor(a.severity)}>{a.severity}</Badge>
                  </div>
                  <Badge variant={a.status === 'active' ? 'destructive' : 'outline'}>{a.status}</Badge>
                </div>
                {a.reaction && <p className="text-sm text-muted-foreground mt-1">Reaction: {a.reaction}</p>}
                {a.onset_date && <p className="text-xs text-muted-foreground mt-1">Onset: {a.onset_date}</p>}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
