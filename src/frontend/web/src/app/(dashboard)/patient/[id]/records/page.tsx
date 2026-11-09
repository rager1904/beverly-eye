'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, ArrowLeft, Loader2, Calendar, User, Stethoscope } from 'lucide-react';
import Link from 'next/link';
import { formatDateTime } from '@/lib/utils';

interface ClinicalNote {
  id: string;
  note_type: string;
  title: string;
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
  authored_by: string;
  authored_datetime: string;
  encounter_id?: string;
}

export default function PatientRecordsPage() {
  const params = useParams();
  const router = useRouter();
  const [records, setRecords] = useState<ClinicalNote[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    try {
      const token = useAuthStore.getState().accessToken;
      const res = await fetch(`/api/v1/emr/notes?patient_id=${params.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setRecords(data.items || data || []);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => { fetchRecords(); }, [fetchRecords]);

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
            <FileText className="h-6 w-6 text-healthcare-blue" />
            Medical Records
          </h1>
          <p className="text-muted-foreground">Patient clinical notes and medical history</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : records.length === 0 ? (
        <Card><CardContent className="text-center py-8 text-muted-foreground">
          <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No medical records found for this patient</p>
        </CardContent></Card>
      ) : (
        <div className="space-y-4">
          {records.map((note) => (
            <Card key={note.id} className="cursor-pointer hover:bg-accent/50 transition-colors" onClick={() => router.push(`/clinical-notes?note=${note.id}`)}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Stethoscope className="h-5 w-5 text-muted-foreground" />
                    <span className="font-medium">{note.title || `${note.note_type} Note`}</span>
                    <Badge variant="outline">{note.note_type}</Badge>
                  </div>
                  <Badge>{note.authored_by}</Badge>
                </div>
                <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                  <span>{note.authored_datetime ? formatDateTime(note.authored_datetime) : '-'}</span>
                </div>
                {note.assessment && <p className="text-sm mt-2 line-clamp-2">{note.assessment}</p>}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
