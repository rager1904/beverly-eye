'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Pill, ArrowLeft, Loader2, Plus } from 'lucide-react';
import Link from 'next/link';

interface Medication {
  id: string;
  medication_name: string;
  generic_name?: string;
  dosage?: string;
  dosage_unit?: string;
  frequency?: string;
  route?: string;
  status: string;
  start_date?: string;
  end_date?: string;
  is_antibiotic?: boolean;
  prescribed_by?: string;
}

export default function PatientMedicationsPage() {
  const params = useParams();
  const router = useRouter();
  const [medications, setMedications] = useState<Medication[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchMedications = useCallback(async () => {
    setLoading(true);
    try {
      const token = useAuthStore.getState().accessToken;
      const res = await fetch(`/api/v1/emr/patients/${params.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setMedications((data.data?.medications || data.medications || []));
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => { fetchMedications(); }, [fetchMedications]);

  const statusColor = (s: string) => {
    switch (s) {
      case 'prescribed': return 'bg-blue-100 text-blue-800';
      case 'administered': return 'bg-green-100 text-green-800';
      case 'completed': return 'bg-gray-100 text-gray-800';
      case 'discontinued': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href={`/patient/${params.id}`}><ArrowLeft className="h-4 w-4 mr-1" />Back to Patient</Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-2 mt-2">
            <Pill className="h-6 w-6 text-green-600" />
            Medications
          </h1>
          <p className="text-muted-foreground">Current and past medications</p>
        </div>
        <Button variant="outline"><Plus className="h-4 w-4 mr-2" />Add Medication</Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : medications.length === 0 ? (
        <Card><CardContent className="text-center py-8 text-muted-foreground">
          <Pill className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No medications recorded for this patient</p>
        </CardContent></Card>
      ) : (
        <div className="space-y-3">
          {medications.map((med) => (
            <Card key={med.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{med.medication_name}</span>
                    {med.is_antibiotic && <Badge variant="outline" className="text-red-600 border-red-300">Antibiotic</Badge>}
                    <Badge variant="outline" className={statusColor(med.status)}>{med.status}</Badge>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4 mt-2 text-sm">
                  {med.dosage && <div><span className="text-muted-foreground">Dosage:</span> {med.dosage} {med.dosage_unit || ''}</div>}
                  {med.frequency && <div><span className="text-muted-foreground">Frequency:</span> {med.frequency}</div>}
                  {med.route && <div><span className="text-muted-foreground">Route:</span> {med.route}</div>}
                  {med.start_date && <div><span className="text-muted-foreground">Start:</span> {med.start_date}</div>}
                  {med.end_date && <div><span className="text-muted-foreground">End:</span> {med.end_date}</div>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
