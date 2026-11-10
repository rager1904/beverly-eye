'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api-client';
import { VideoCall, type IceServerConfig } from '@/components/telemedicine/VideoCall';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2, Video } from 'lucide-react';

interface InviteJoinResponse {
  consultation_id: string;
  status: string;
  consultation_type: string;
  ice_servers: IceServerConfig[];
}

export default function JoinTelemedicinePage() {
  const params = useParams<{ id: string }>();
  const tokenRef = useRef<string | null>(null);
  const [inviteToken, setInviteToken] = useState('');
  const [iceServers, setIceServers] = useState<IceServerConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [ended, setEnded] = useState(false);
  const [joined, setJoined] = useState(false);

  useEffect(() => {
    const storageKey = `telemedicine-invite:${params.id}`;
    if (!tokenRef.current) {
      const fragment = new URLSearchParams(window.location.hash.slice(1));
      tokenRef.current = fragment.get('invite') || window.sessionStorage.getItem(storageKey);
      if (tokenRef.current) {
        window.sessionStorage.setItem(storageKey, tokenRef.current);
        // Keep the bearer invite out of subsequent browser history and referrers.
        window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
      }
    }

    const token = tokenRef.current;
    if (!token) {
      setError('This invitation link is incomplete. Ask the care provider to send a new one.');
      setLoading(false);
      return;
    }

    let cancelled = false;
    api.request<InviteJoinResponse>(`/telemedicine/invites/${encodeURIComponent(String(params.id))}/join`, {
      method: 'POST',
      skipAuth: true,
      headers: { 'X-Call-Invite-Token': token },
    }).then((response) => {
      if (cancelled) return;
      if (response.consultation_id !== params.id || ['completed', 'cancelled', 'no_show'].includes(response.status)) {
        setError('This consultation has ended. Ask the care provider to schedule another call.');
        window.sessionStorage.removeItem(storageKey);
        return;
      }
      setInviteToken(token);
      setIceServers(response.ice_servers || []);
    }).catch((joinError) => {
      if (!cancelled) {
        window.sessionStorage.removeItem(storageKey);
        setError(joinError instanceof Error ? joinError.message : 'Unable to join this call');
      }
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });

    return () => { cancelled = true; };
  }, [params.id]);

  const leaveCall = () => {
    window.sessionStorage.removeItem(`telemedicine-invite:${params.id}`);
    setEnded(true);
  };

  if (loading) {
    return <main className="flex min-h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-healthcare-green" /></main>;
  }

  if (ended) {
    return (
      <main className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-lg"><CardContent className="space-y-4 p-6 text-center">
          <Video className="mx-auto h-10 w-10 text-healthcare-green" />
          <h1 className="text-xl font-semibold">You left the consultation</h1>
          <p className="text-sm text-muted-foreground">You can close this page. Contact your care provider if you need to rejoin.</p>
        </CardContent></Card>
      </main>
    );
  }

  if (error || !inviteToken) {
    return (
      <main className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-lg"><CardContent className="space-y-4 p-6 text-center">
          <Video className="mx-auto h-10 w-10 text-healthcare-green" />
          <h1 className="text-xl font-semibold">Unable to join the call</h1>
          <p role="alert" className="text-sm text-muted-foreground">{error || 'Invalid invitation.'}</p>
          <Button variant="outline" asChild><Link href="/">Return to UbuntuCare</Link></Button>
        </CardContent></Card>
      </main>
    );
  }

  if (!joined) {
    return (
      <main className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-lg"><CardContent className="space-y-4 p-6 text-center">
          <Video className="mx-auto h-10 w-10 text-healthcare-green" />
          <h1 className="text-xl font-semibold">Join your video consultation</h1>
          <p className="text-sm text-muted-foreground">
            Joining shares your camera and microphone with the care provider. Audio and video are not recorded.
            Chat messages are temporarily relayed during the call. This private invitation expires after one hour.
            You can mute or turn off video at any time.
          </p>
          <Button onClick={() => setJoined(true)}>Join and enable camera</Button>
        </CardContent></Card>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-2 sm:p-4">
      <div className="mx-auto max-w-6xl space-y-3">
        <div>
          <p className="text-sm font-semibold text-healthcare-green">UbuntuCare secure telemedicine</p>
          <p className="text-xs text-muted-foreground">This invite grants access to this consultation only. Do not forward it.</p>
        </div>
        <VideoCall
          sessionId={String(params.id)}
          participantName="Care provider"
          participantRole="Healthcare provider"
          localRole="patient"
          inviteToken={inviteToken}
          iceServers={iceServers}
          onEnd={leaveCall}
        />
      </div>
    </main>
  );
}
