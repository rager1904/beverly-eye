'use client';

import { useState, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Mic, Square, Loader2, FileText, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '@/lib/auth';

interface VoiceRecorderProps {
  onTranscriptionComplete: (text: string) => void;
  language?: string;
}

export function VoiceRecorder({ onTranscriptionComplete, language = 'en' }: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval>>();
  const token = useAuthStore((s) => s.accessToken);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setIsProcessing(true);
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        await transcribeAudio(audioBlob);
      };

      mediaRecorder.start(1000);
      setIsRecording(true);
      setDuration(0);
      timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000);
    } catch (err) {
      setError('Microphone access denied. Please allow microphone permissions.');
      toast.error('Microphone access denied');
    }
  }, [language, token]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    clearInterval(timerRef.current);
  }, []);

  const transcribeAudio = async (audioBlob: Blob) => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');
      formData.append('language', language);

      const response = await fetch('/api/v1/asr/transcribe', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        onTranscriptionComplete(data.text);
        toast.success('Transcription complete');
      } else {
        throw new Error('Transcription failed');
      }
    } catch {
      toast.error('Transcription failed. Check connection and try again.');
    }
    setIsProcessing(false);
  };

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <Card className={`border-2 ${isRecording ? 'border-red-400 bg-red-50/50' : 'border-dashed'}`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {isRecording ? (
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
                <span className="font-mono text-lg font-bold">{formatDuration(duration)}</span>
                <Badge variant="critical" className="animate-pulse-slow">Recording</Badge>
              </div>
            ) : isProcessing ? (
              <div className="flex items-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin text-healthcare-blue" />
                <span className="text-sm text-muted-foreground">Transcribing audio...</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Mic className="h-5 w-5 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Record clinical notes</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {error && (
              <div className="flex items-center gap-1 text-xs text-red-500">
                <AlertCircle className="h-3 w-3" />{error}
              </div>
            )}
            {isRecording ? (
              <Button variant="destructive" size="sm" onClick={stopRecording}>
                <Square className="h-4 w-4 mr-1" />Stop
              </Button>
            ) : (
              <Button variant="outline" size="sm" onClick={startRecording} disabled={isProcessing}>
                <Mic className="h-4 w-4 mr-1" />
                {isProcessing ? 'Processing...' : 'Record'}
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
