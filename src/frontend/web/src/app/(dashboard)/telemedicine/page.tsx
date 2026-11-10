'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuthStore } from '@/lib/auth';
import { api } from '@/lib/api-client';
import { PatientPicker } from '@/components/PatientPicker';
import { VideoCall, type IceServerConfig } from '@/components/telemedicine/VideoCall';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { CalendarClock, Clipboard, Loader2, Phone, Video } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';

type ConsultationStatus = 'scheduled' | 'in_waiting_room' | 'in_progress' | 'completed' | 'cancelled' | 'no_show';

interface Consultation {
  id: string;
  patient_id: string;
  provider_id: string;
  consultation_type: 'video' | 'audio' | 'chat' | 'phone';
  status: ConsultationStatus;
  scheduled_start?: string | null;
  actual_start?: string | null;
  created_at: string;
}

interface ConsultationList {
  items: Consultation[];
  total: number;
}

interface ConsultationCreated {
  consultation: Consultation;
  invite_token: string;
  ice_servers: IceServerConfig[];
}

interface WaitingRoom {
  patient_joined_at?: string | null;
}

interface RenewedInvite {
  invite_token: string;
  expires_at: string;
}

interface MediaConfig {
  ice_servers: IceServerConfig[];
}

interface ActiveCall {
  consultation: Consultation;
  inviteToken?: string;
  iceServers: IceServerConfig[];
}

const STAFF_ROLES = new Set(['admin', 'provider', 'nurse', 'clinical_officer']);

export default function TelemedicinePage() {
  const user = useAuthStore((state) => state.user);
  const canStartCall = Boolean(user && STAFF_ROLES.has(user.role));
  const [patientId, setPatientId] = useState('');
  const [sessions, setSessions] = useState<Consultation[]>([]);
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');
  const [activeCall, setActiveCall] = useState<ActiveCall | null>(null);

  const listEndpoint = useMemo(() => {
    if (!user || !canStartCall) return null;
    const params = new URLSearchParams({ per_page: '50' });
    if (user.role !== 'admin') params.set('provider_id', user.id);
    return `/telemedicine/consultations?${params.toString()}`;
  }, [canStartCall, user]);

  const loadSessions = useCallback(async () => {
    if (!listEndpoint) return;
    setLoading(true);
    try {
      const response = await api.get<ConsultationList>(listEndpoint);
      setSessions(response.items || []);
      setError('');
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load consultations');
    } finally {
      setLoading(false);
    }
  }, [listEndpoint]);

  useEffect(() => {
    void loadSessions();
    if (!listEndpoint) return;
    const timer = window.setInterval(() => void loadSessions(), 15000);
    return () => window.clearInterval(timer);
  }, [listEndpoint, loadSessions]);

  const startCall = async () => {
    if (!patientId || !user) {
      toast.error('Select a registered patient first.');
      return;
    }
    setStarting(true);
    setError('');
    try {
      const created = await api.post<ConsultationCreated>('/telemedicine/consultations', {
        patient_id: patientId,
        provider_id: user.id,
        consultation_type: 'video',
      });
      const started = await api.post<Consultation>(
        `/telemedicine/consultations/${created.consultation.id}/start`,
        {},
      );
      setActiveCall({
        consultation: started,
        inviteToken: created.invite_token,
        iceServers: created.ice_servers,
      });
      await loadSessions();
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : 'Unable to start the consultation');
    } finally {
      setStarting(false);
    }
  };

  const joinExistingCall = async (consultation: Consultation) => {
    try {
      const waitingRoom = await api.get<WaitingRoom>(`/telemedicine/consultations/${consultation.id}/waiting-room`);
      let inviteToken: string | undefined;
      if (!waitingRoom.patient_joined_at) {
        const invite = await api.get<RenewedInvite>(`/telemedicine/consultations/${consultation.id}/token`);
        inviteToken = invite.invite_token;
      }
      const mediaConfig = await api.get<MediaConfig>(`/telemedicine/consultations/${consultation.id}/ice-servers`);
      const started = await api.post<Consultation>(`/telemedicine/consultations/${consultation.id}/start`, {});
      setActiveCall({ consultation: started, inviteToken, iceServers: mediaConfig.ice_servers });
    } catch (joinError) {
      toast.error(joinError instanceof Error ? joinError.message : 'Unable to join the consultation');
    }
  };

  const endCall = async () => {
    if (!activeCall) return;
    try {
      await api.post(`/telemedicine/consultations/${activeCall.consultation.id}/complete`, {});
      toast.success('Consultation ended and saved.');
    } catch (endError) {
      toast.error(endError instanceof Error ? endError.message : 'Unable to save the consultation end');
      return;
    }
    setActiveCall(null);
    setPatientId('');
    await loadSessions();
  };

  const copyInvite = async () => {
    if (!activeCall?.inviteToken) return;
    const url = `${window.location.origin}/telemedicine/join/${activeCall.consultation.id}#invite=${encodeURIComponent(activeCall.inviteToken)}`;
    try {
      await navigator.clipboard.writeText(url);
      toast.success('Secure patient invite link copied. Send it through a private channel.');
    } catch {
      toast.error('Could not copy the invite link. Use the browser address bar after enabling secure clipboard access.');
    }
  };

  if (activeCall) {
    return (
      <div className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-xl font-bold sm:text-2xl">
              <Video className="h-6 w-6 text-healthcare-blue" /> Video consultation
            </h1>
            <p className="text-sm text-muted-foreground">Session {activeCall.consultation.id.slice(0, 8)}</p>
          </div>
          {activeCall.inviteToken && (
            <Button variant="outline" onClick={() => void copyInvite()}>
              <Clipboard className="mr-2 h-4 w-4" /> Copy patient invite
            </Button>
          )}
        </div>
        <VideoCall
          sessionId={activeCall.consultation.id}
          participantName="Patient"
          participantRole="Patient"
          localRole="provider"
          inviteToken={activeCall.inviteToken}
          iceServers={activeCall.iceServers}
          onEnd={endCall}
        />
      </div>
    );
  }

  if (!canStartCall) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <h1 className="flex items-center gap-2 text-2xl font-bold"><Video className="h-6 w-6 text-healthcare-blue" />Telemedicine</h1>
        <Card><CardContent className="space-y-2 p-6 text-sm">
          <p className="font-medium">Join a consultation</p>
          <p className="text-muted-foreground">Open the private invite link provided by your care team. The link is valid for one hour and only grants access to that call.</p>
        </CardContent></Card>
      </div>
    );
  }

  const upcoming = sessions.filter((session) => ['scheduled', 'in_waiting_room'].includes(session.status));
  const active = sessions.filter((session) => session.status === 'in_progress');
  const past = sessions.filter((session) => ['completed', 'cancelled', 'no_show'].includes(session.status));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-bold sm:text-2xl"><Video className="h-6 w-6 text-healthcare-blue" />Telemedicine</h1>
        <p className="mt-1 text-sm text-muted-foreground">Start a secure video consultation with a registered patient.</p>
      </div>

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Phone className="h-4 w-4" />Start a video call</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <PatientPicker value={patientId} onChange={setPatientId} />
          <p className="text-xs text-muted-foreground">The patient must be registered at your assigned hospital before a call can start. <Link className="underline underline-offset-2" href="/patient/register">Register a patient</Link></p>
          <Button onClick={() => void startCall()} disabled={!patientId || starting}>
            {starting ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Starting…</> : <><Video className="mr-2 h-4 w-4" />Start video call</>}
          </Button>
          <p className="text-xs text-muted-foreground">After the call starts, copy the secure invite link and send it to the patient privately.</p>
        </CardContent>
      </Card>

      {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Your consultations</CardTitle>
          <Button variant="outline" size="sm" onClick={() => void loadSessions()} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Refresh'}
          </Button>
        </CardHeader>
        <CardContent className="space-y-6">
          {loading && sessions.length === 0 ? (
            <div className="flex justify-center p-6"><Loader2 className="h-5 w-5 animate-spin" /></div>
          ) : sessions.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">No consultations yet.</p>
          ) : (
            <>
              {[['Waiting', upcoming], ['Active', active], ['History', past]].map(([label, items]) => (
                <section key={label as string} className="space-y-2">
                  <h2 className="text-sm font-semibold">{label as string} ({(items as Consultation[]).length})</h2>
                  {(items as Consultation[]).length === 0 ? (
                    <p className="text-xs text-muted-foreground">None</p>
                  ) : (items as Consultation[]).map((consultation) => (
                    <div key={consultation.id} className="flex flex-col gap-3 rounded-md border p-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">Patient {consultation.patient_id.slice(0, 8)}</p>
                        <p className="text-xs text-muted-foreground">{consultation.scheduled_start ? formatDateTime(consultation.scheduled_start) : consultation.status.replaceAll('_', ' ')}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={consultation.status === 'in_progress' ? 'success' : 'secondary'}>{consultation.status.replaceAll('_', ' ')}</Badge>
                        {consultation.status !== 'completed' && consultation.status !== 'cancelled' && consultation.status !== 'no_show' && (
                          <Button size="sm" variant="outline" onClick={() => void joinExistingCall(consultation)}>
                            <Video className="mr-1 h-4 w-4" /> {consultation.status === 'in_progress' ? 'Rejoin' : 'Start'}
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </section>
              ))}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
