'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api-client';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  AlertCircle,
  Loader2,
  MessageSquare,
  Mic,
  MicOff,
  Monitor,
  PhoneOff,
  Video,
  VideoOff,
} from 'lucide-react';

export interface IceServerConfig {
  urls: string | string[];
  username?: string;
  credential?: string;
}

interface SignalEnvelope {
  type: 'offer' | 'answer' | 'ice_candidate' | 'chat' | 'hangup';
  sender_role: 'provider' | 'patient';
  payload: Record<string, unknown>;
  sent_at: string;
}

interface SignalBatch {
  items: SignalEnvelope[];
  next_cursor: number;
}

interface ChatMessage {
  id: string;
  senderRole: 'provider' | 'patient';
  text: string;
  sentAt: Date;
}

interface VideoCallProps {
  sessionId: string;
  participantName: string;
  participantRole: string;
  localRole: 'provider' | 'patient';
  inviteToken?: string;
  iceServers?: IceServerConfig[];
  onEnd: () => void | Promise<void>;
}

const FALLBACK_ICE_SERVERS: IceServerConfig[] = [
  { urls: ['stun:stun.l.google.com:19302', 'stun:stun1.l.google.com:19302'] },
];

const pollDelay = (milliseconds: number, signal: AbortSignal) => new Promise<void>((resolve) => {
  if (signal.aborted) return resolve();
  let timer: number;
  const onAbort = () => {
    window.clearTimeout(timer);
    signal.removeEventListener('abort', onAbort);
    resolve();
  };
  timer = window.setTimeout(() => {
    signal.removeEventListener('abort', onAbort);
    resolve();
  }, milliseconds);
  signal.addEventListener('abort', onAbort, { once: true });
});

export function VideoCall({
  sessionId,
  participantName,
  participantRole,
  localRole,
  inviteToken,
  iceServers,
  onEnd,
}: VideoCallProps) {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [mediaReady, setMediaReady] = useState(false);
  const [remoteReady, setRemoteReady] = useState(false);
  const [connectionState, setConnectionState] = useState<RTCPeerConnectionState>('new');
  const [error, setError] = useState('');
  const [ending, setEnding] = useState(false);
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const remoteStreamRef = useRef<MediaStream | null>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const cursorRef = useRef(0);
  const candidateQueueRef = useRef<RTCIceCandidateInit[]>([]);
  const inviteMode = Boolean(inviteToken && localRole === 'patient');
  const signalEndpoint = inviteMode
    ? `/telemedicine/invites/${sessionId}/signals`
    : `/telemedicine/consultations/${sessionId}/signals`;

  const apiConfig = useCallback((signal?: AbortSignal) => ({
    signal,
    skipAuth: inviteMode,
    headers: inviteToken ? { 'X-Call-Invite-Token': inviteToken } : undefined,
  }), [inviteMode, inviteToken]);

  const sendSignal = useCallback(async (
    type: SignalEnvelope['type'],
    payload: Record<string, unknown> = {},
  ) => {
    await api.post(signalEndpoint, { type, payload }, apiConfig());
  }, [apiConfig, signalEndpoint]);

  const acceptCandidate = useCallback(async (candidate: RTCIceCandidateInit) => {
    const peer = peerConnectionRef.current;
    if (!peer) return;
    if (!peer.remoteDescription) {
      candidateQueueRef.current.push(candidate);
      return;
    }
    try {
      await peer.addIceCandidate(new RTCIceCandidate(candidate));
    } catch (candidateError) {
      console.warn('Ignoring invalid/expired ICE candidate', candidateError);
    }
  }, []);

  const drainCandidateQueue = useCallback(async () => {
    const queued = candidateQueueRef.current.splice(0);
    for (const candidate of queued) await acceptCandidate(candidate);
  }, [acceptCandidate]);

  const handleSignal = useCallback(async (message: SignalEnvelope) => {
    const peer = peerConnectionRef.current;
    if (!peer || message.sender_role === localRole) return;

    if (message.type === 'offer' && localRole === 'patient') {
      await peer.setRemoteDescription(new RTCSessionDescription(message.payload as unknown as RTCSessionDescriptionInit));
      await drainCandidateQueue();
      const answer = await peer.createAnswer();
      await peer.setLocalDescription(answer);
      await sendSignal('answer', {
        type: answer.type,
        sdp: answer.sdp,
      });
      return;
    }

    if (message.type === 'answer' && localRole === 'provider') {
      await peer.setRemoteDescription(new RTCSessionDescription(message.payload as unknown as RTCSessionDescriptionInit));
      await drainCandidateQueue();
      return;
    }

    if (message.type === 'ice_candidate') {
      const candidate = message.payload as RTCIceCandidateInit;
      if (candidate.candidate) await acceptCandidate(candidate);
      return;
    }

    if (message.type === 'chat' && typeof message.payload.text === 'string') {
      setMessages((current) => [...current, {
        id: `${message.sender_role}-${message.sent_at}-${current.length}`,
        senderRole: message.sender_role,
        text: message.payload.text as string,
        sentAt: new Date(message.sent_at),
      }]);
      return;
    }

    if (message.type === 'hangup') {
      setError(`${participantRole} left the call.`);
      setConnectionState('disconnected');
    }
  }, [acceptCandidate, drainCandidateQueue, localRole, participantRole, sendSignal]);

  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;

    const start = async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError('This browser does not support camera and microphone access. Open the secure HTTPS site in a current browser.');
        setConnectionState('failed');
        return;
      }

      let localStream: MediaStream;
      try {
        localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
      } catch (mediaError) {
        const name = mediaError instanceof DOMException ? mediaError.name : '';
        const message = name === 'NotAllowedError'
          ? 'Allow camera and microphone access in your browser, then retry the call.'
          : name === 'NotFoundError'
            ? 'No camera or microphone was found on this device.'
            : 'Could not start the camera and microphone. Check device permissions and try again.';
        setError(message);
        setConnectionState('failed');
        return;
      }

      if (disposed) {
        localStream.getTracks().forEach((track) => track.stop());
        return;
      }

      localStreamRef.current = localStream;
      if (localVideoRef.current) localVideoRef.current.srcObject = localStream;
      setMediaReady(true);

      const peer = new RTCPeerConnection({
        iceServers: iceServers?.length ? iceServers : FALLBACK_ICE_SERVERS,
      });
      peerConnectionRef.current = peer;
      localStream.getTracks().forEach((track) => peer.addTrack(track, localStream));

      peer.onicecandidate = (event) => {
        if (!disposed && event.candidate) {
          void sendSignal('ice_candidate', { ...event.candidate.toJSON() }).catch((signalError) => {
            if (!disposed) setError(signalError instanceof Error ? signalError.message : 'Unable to send network candidate');
          });
        }
      };

      peer.ontrack = (event) => {
        if (disposed) return;
        const remoteStream = event.streams[0] ?? new MediaStream([event.track]);
        remoteStreamRef.current = remoteStream;
        if (remoteVideoRef.current) remoteVideoRef.current.srcObject = remoteStream;
        setRemoteReady(true);
      };

      peer.onconnectionstatechange = () => {
        if (disposed) return;
        setConnectionState(peer.connectionState);
        if (peer.connectionState === 'failed') {
          setError('The video connection failed. Your network may require a TURN relay; ask your administrator to configure one.');
        } else if (peer.connectionState === 'connected') {
          setError('');
        }
      };

      const pollSignals = async () => {
        while (!disposed && !controller.signal.aborted) {
          try {
            const batch = await api.get<SignalBatch>(
              `${signalEndpoint}?cursor=${cursorRef.current}`,
              apiConfig(controller.signal),
            );
            cursorRef.current = batch.next_cursor;
            for (const message of batch.items) await handleSignal(message);
          } catch (pollError) {
            if (!disposed && !controller.signal.aborted) {
              setError(pollError instanceof Error ? pollError.message : 'Call signaling was interrupted');
            }
          }
          await pollDelay(800, controller.signal);
        }
      };
      void pollSignals();

      if (localRole === 'provider') {
        try {
          const offer = await peer.createOffer();
          await peer.setLocalDescription(offer);
          await sendSignal('offer', { type: offer.type, sdp: offer.sdp });
          setConnectionState('connecting');
        } catch (offerError) {
          setError(offerError instanceof Error ? offerError.message : 'Unable to start the video call');
          setConnectionState('failed');
        }
      } else {
        setConnectionState('connecting');
      }
    };

    void start();

    return () => {
      disposed = true;
      controller.abort();
      peerConnectionRef.current?.close();
      peerConnectionRef.current = null;
      localStreamRef.current?.getTracks().forEach((track) => track.stop());
      screenStreamRef.current?.getTracks().forEach((track) => {
        track.onended = null;
        track.stop();
      });
      remoteStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, [apiConfig, handleSignal, iceServers, localRole, sendSignal, sessionId, signalEndpoint]);

  const toggleMute = useCallback(() => {
    const enabled = isMuted;
    localStreamRef.current?.getAudioTracks().forEach((track) => { track.enabled = enabled; });
    setIsMuted(!enabled);
  }, [isMuted]);

  const toggleVideo = useCallback(() => {
    const enabled = isVideoOff;
    const sender = peerConnectionRef.current?.getSenders().find((item) => item.track?.kind === 'video');
    if (sender?.track) sender.track.enabled = enabled;
    localStreamRef.current?.getVideoTracks().forEach((track) => { track.enabled = enabled; });
    setIsVideoOff(!enabled);
  }, [isVideoOff]);

  const toggleScreenShare = useCallback(async () => {
    const peer = peerConnectionRef.current;
    const videoSender = peer?.getSenders().find((sender) => sender.track?.kind === 'video');
    if (!peer || !videoSender) return;

    const restoreCamera = async () => {
      const screenStream = screenStreamRef.current;
      screenStream?.getTracks().forEach((track) => track.stop());
      screenStreamRef.current = null;
      let cameraTrack = localStreamRef.current?.getVideoTracks()[0];
      if (!cameraTrack || cameraTrack.readyState === 'ended') {
        const camera = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        cameraTrack = camera.getVideoTracks()[0];
        if (!cameraTrack) throw new Error('No camera track is available');
        localStreamRef.current?.addTrack(cameraTrack);
      }
      if (!cameraTrack) throw new Error('No camera track is available');
      await videoSender.replaceTrack(cameraTrack);
      if (localVideoRef.current && localStreamRef.current) localVideoRef.current.srcObject = localStreamRef.current;
      setIsScreenSharing(false);
    };

    if (isScreenSharing) {
      try {
        await restoreCamera();
      } catch {
        setError('Unable to restore your camera. Re-enable video or rejoin the call.');
      }
      return;
    }

    try {
      const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      const screenTrack = screenStream.getVideoTracks()[0];
      if (!screenTrack) return;
      screenStreamRef.current = screenStream;
      await videoSender.replaceTrack(screenTrack);
      if (localVideoRef.current) localVideoRef.current.srcObject = screenStream;
      screenTrack.onended = () => { void restoreCamera(); };
      setIsScreenSharing(true);
    } catch (shareError) {
      if (shareError instanceof DOMException && shareError.name !== 'NotAllowedError') {
        setError('Screen sharing could not be started.');
      }
    }
  }, [isScreenSharing]);

  const sendChatMessage = useCallback(async () => {
    const text = newMessage.trim();
    if (!text) return;
    try {
      await sendSignal('chat', { text });
      setMessages((current) => [...current, {
        id: `local-${Date.now()}-${current.length}`,
        senderRole: localRole,
        text,
        sentAt: new Date(),
      }]);
      setNewMessage('');
    } catch (chatError) {
      setError(chatError instanceof Error ? chatError.message : 'Unable to send message');
    }
  }, [localRole, newMessage, sendSignal]);

  const endCall = useCallback(async () => {
    if (ending) return;
    setEnding(true);
    try { await sendSignal('hangup', {}); } catch { /* the call is ending anyway */ }
    await onEnd();
  }, [ending, onEnd, sendSignal]);

  const statusText = connectionState === 'failed'
    ? 'Connection failed'
    : !mediaReady
      ? 'Starting camera and microphone…'
    : connectionState === 'connected' && remoteReady
      ? 'Connected'
      : 'Waiting for the other participant';

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        <div className="relative aspect-video min-h-64 bg-slate-950">
          <video ref={remoteVideoRef} autoPlay playsInline className="h-full w-full object-cover" />
          {!remoteReady && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center text-white">
              {connectionState === 'failed' ? <AlertCircle className="h-10 w-10 text-red-400" /> : <Loader2 className="h-8 w-8 animate-spin" />}
              <p className="font-medium">{statusText}</p>
              {!error && mediaReady && <p className="max-w-md text-sm text-white/70">Send the secure invite link to the patient. The call connects when they join.</p>}
            </div>
          )}
          <div className="absolute bottom-3 right-3 h-24 w-36 overflow-hidden rounded-lg border border-white/30 bg-slate-800 shadow-lg sm:bottom-4 sm:right-4 sm:h-32 sm:w-48">
            <video ref={localVideoRef} autoPlay playsInline muted className="h-full w-full object-cover [transform:scaleX(-1)]" />
            {!mediaReady && <div className="absolute inset-0 flex items-center justify-center text-xs text-white/70">Camera preview</div>}
          </div>
          <div className="absolute left-3 top-3 flex flex-col gap-2 sm:left-4 sm:top-4">
            <Badge className={connectionState === 'connected' && remoteReady ? 'bg-green-600 text-white' : connectionState === 'failed' ? 'bg-red-600 text-white' : 'bg-amber-500 text-white'}>
              {statusText}
            </Badge>
            {error && <p role="alert" className="max-w-sm rounded bg-black/70 px-3 py-2 text-xs text-white">{error}</p>}
          </div>
          <div className="absolute bottom-3 left-3 rounded bg-black/50 px-2 py-1 text-white sm:bottom-4 sm:left-4">
            <p className="text-sm font-medium">{participantName}</p>
            <p className="text-xs opacity-80">{participantRole}</p>
          </div>
        </div>

        {showChat && (
          <div className="border-t bg-card">
            <div className="max-h-48 space-y-2 overflow-y-auto p-3" aria-live="polite">
              {messages.length === 0 && <p className="text-sm text-muted-foreground">No messages yet.</p>}
              {messages.map((message) => (
                <div key={message.id} className={`flex ${message.senderRole === localRole ? 'justify-end' : 'justify-start'}`}>
                  <div className="max-w-[85%] rounded-lg bg-muted px-3 py-2 text-sm">
                    <p>{message.text}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{message.sentAt.toLocaleTimeString()}</p>
                  </div>
                </div>
              ))}
            </div>
            <form className="flex gap-2 border-t p-3" onSubmit={(event) => { event.preventDefault(); void sendChatMessage(); }}>
              <input
                value={newMessage}
                onChange={(event) => setNewMessage(event.target.value)}
                maxLength={1000}
                className="h-10 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm"
                placeholder="Message the other participant"
                aria-label="Chat message"
              />
              <Button type="submit" size="sm" disabled={!newMessage.trim()}>Send</Button>
            </form>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-center gap-2 border-t bg-card p-3 sm:gap-3 sm:p-4">
          <Button variant="outline" size="icon" onClick={toggleMute} disabled={!mediaReady} title={isMuted ? 'Unmute microphone' : 'Mute microphone'} aria-label={isMuted ? 'Unmute microphone' : 'Mute microphone'}>
            {isMuted ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </Button>
          <Button variant="outline" size="icon" onClick={toggleVideo} disabled={!mediaReady} title={isVideoOff ? 'Enable camera' : 'Disable camera'} aria-label={isVideoOff ? 'Enable camera' : 'Disable camera'}>
            {isVideoOff ? <VideoOff className="h-5 w-5" /> : <Video className="h-5 w-5" />}
          </Button>
          <Button variant="outline" size="icon" onClick={() => void toggleScreenShare()} disabled={!mediaReady} title={isScreenSharing ? 'Stop screen sharing' : 'Share screen'} aria-label={isScreenSharing ? 'Stop screen sharing' : 'Share screen'}>
            <Monitor className="h-5 w-5" />
          </Button>
          <Button variant="outline" size="icon" onClick={() => setShowChat((current) => !current)} title={showChat ? 'Hide chat' : 'Show chat'} aria-label={showChat ? 'Hide chat' : 'Show chat'}>
            <MessageSquare className="h-5 w-5" />
          </Button>
          <Button variant="destructive" size="icon" onClick={() => void endCall()} disabled={ending} title="End call" aria-label="End call">
            <PhoneOff className="h-5 w-5" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
