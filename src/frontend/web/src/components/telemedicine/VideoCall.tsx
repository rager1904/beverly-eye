'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Mic, MicOff, Video, VideoOff, PhoneOff, Monitor, MessageSquare } from 'lucide-react';

interface VideoCallProps {
  sessionId: string;
  onEnd: () => void;
  participantName: string;
  participantRole: string;
}

export function VideoCall({ sessionId, onEnd, participantName, participantRole }: VideoCallProps) {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'poor' | 'disconnected'>('connecting');
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    async function setupMedia() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        if (localVideoRef.current) localVideoRef.current.srcObject = stream;
        localStreamRef.current = stream;
        setConnectionStatus('connected');

        const config: RTCConfiguration = {
          iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
          ],
        };
        const pc = new RTCPeerConnection(config);
        stream.getTracks().forEach((track) => pc.addTrack(track, stream));
        peerConnectionRef.current = pc;
      } catch (err) {
        console.error('Media setup failed:', err);
        setConnectionStatus('disconnected');
      }
    }
    setupMedia();
    return () => {
      localStreamRef.current?.getTracks().forEach((t) => t.stop());
      peerConnectionRef.current?.close();
    };
  }, [sessionId]);

  const toggleMute = useCallback(() => {
    localStreamRef.current?.getAudioTracks().forEach((track) => { track.enabled = isMuted; });
    setIsMuted(!isMuted);
  }, [isMuted]);

  const toggleVideo = useCallback(() => {
    localStreamRef.current?.getVideoTracks().forEach((track) => { track.enabled = isVideoOff; });
    setIsVideoOff(!isVideoOff);
  }, [isVideoOff]);

  const toggleScreenShare = useCallback(async () => {
    if (isScreenSharing) {
      localStreamRef.current?.getVideoTracks().forEach((t) => t.stop());
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (localVideoRef.current) localVideoRef.current.srcObject = stream;
      localStreamRef.current = stream;
      setIsScreenSharing(false);
    } else {
      try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        if (localVideoRef.current) localVideoRef.current.srcObject = screenStream;
        localStreamRef.current = screenStream;
        setIsScreenSharing(true);
      } catch { /* user cancelled */ }
    }
  }, [isScreenSharing]);

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0 relative">
        <div className="relative bg-black aspect-video">
          <video ref={remoteVideoRef} autoPlay playsInline className="w-full h-full object-cover" />
          <div className="absolute bottom-4 right-4 w-48 aspect-video bg-gray-800 rounded-lg overflow-hidden shadow-lg border-2 border-white/20">
            <video ref={localVideoRef} autoPlay playsInline muted className="w-full h-full object-cover mirror" />
          </div>
          <div className="absolute top-4 left-4">
            <Badge className={`${connectionStatus === 'connected' ? 'bg-green-500' : connectionStatus === 'poor' ? 'bg-amber-500' : 'bg-red-500'} text-white`}>
              {connectionStatus === 'connecting' ? 'Connecting...' : connectionStatus === 'connected' ? 'Connected' : connectionStatus === 'poor' ? 'Poor Signal' : 'Disconnected'}
            </Badge>
          </div>
          <div className="absolute bottom-4 left-4">
            <div className="text-white text-sm drop-shadow-lg">
              <p className="font-medium">{participantName}</p>
              <p className="text-xs opacity-80">{participantRole}</p>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-center gap-4 p-4 bg-card border-t">
          <Button
            variant="outline"
            size="icon"
            onClick={toggleMute}
            className={`rounded-full h-12 w-12 ${isMuted ? 'bg-red-100 border-red-300 text-red-600' : ''}`}
          >
            {isMuted ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={toggleVideo}
            className={`rounded-full h-12 w-12 ${isVideoOff ? 'bg-red-100 border-red-300 text-red-600' : ''}`}
          >
            {isVideoOff ? <VideoOff className="h-5 w-5" /> : <Video className="h-5 w-5" />}
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={toggleScreenShare}
            className={`rounded-full h-12 w-12 ${isScreenSharing ? 'bg-blue-100 border-blue-300 text-blue-600' : ''}`}
          >
            <Monitor className="h-5 w-5" />
          </Button>
          <Button
            variant="destructive"
            size="icon"
            onClick={onEnd}
            className="rounded-full h-14 w-14 bg-red-600 hover:bg-red-700"
          >
            <PhoneOff className="h-6 w-6" />
          </Button>
          <Button variant="outline" size="icon" className="rounded-full h-12 w-12">
            <MessageSquare className="h-5 w-5" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
