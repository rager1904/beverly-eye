'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api-client';
import { VideoCall, type IceServerConfig } from '@/components/telemedicine/VideoCall';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

interface Consultation {
  id: string;
  patient_id: string;
  provider_id: string;
  status: string;
}

interface MediaConfig {
  ice_servers: IceServerConfig[];
}

export default function TelemedicineSessionPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [session, setSession] = useState<Consultation | null>(null);
  const [iceServers, setIceServers] = useState<IceServerConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const consultation = await api.get<Consultation>(`/telemedicine/consultations/${encodeURIComponent(params.id)}`);
        const mediaConfig = await api.get<MediaConfig>(`/telemedicine/consultations/${encodeURIComponent(params.id)}/ice-servers`);
        await api.post(`/telemedicine/consultations/${encodeURIComponent(params.id)}/start`, {});
        if (!cancelled) {
          setSession(consultation);
          setIceServers(mediaConfig.ice_servers || []);
        }
      } catch (loadError) {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : 'Unable to open this consultation');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [params.id]);

  const endCall = useCallback(async () => {
    try {
      await api.post(`/telemedicine/consultations/${encodeURIComponent(params.id)}/complete`, {});
      router.replace('/telemedicine');
    } catch (endError) {
      setError(endError instanceof Error ? endError.message : 'Unable to save the completed consultation');
    }
  }, [params.id, router]);

  if (loading) {
    return <div className="flex min-h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>;
  }
  if (error || !session) {
    return (
      <div className="mx-auto max-w-xl space-y-4 rounded-lg border p-6 text-center">
        <p role="alert" className="text-sm text-muted-foreground">{error || 'Consultation not found'}</p>
        <Button variant="outline" onClick={() => router.replace('/telemedicine')}>Back to telemedicine</Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Rejoin video consultation</h1>
      <VideoCall
        sessionId={session.id}
        participantName={`Patient ${session.patient_id.slice(0, 8)}`}
        participantRole="Patient"
        localRole="provider"
        iceServers={iceServers}
        onEnd={endCall}
      />
    </div>
  );
}
