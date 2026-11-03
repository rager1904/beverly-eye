'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Video, VideoOff, Mic, MicOff, PhoneOff, MessageSquare, ArrowLeft, Loader2, User } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

interface Message {
  id: string;
  sender: 'provider' | 'patient';
  text: string;
  timestamp: Date;
}

export default function TelemedicineSessionPage() {
  const params = useParams();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [sessionActive, setSessionActive] = useState(true);
  const [videoEnabled, setVideoEnabled] = useState(true);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', sender: 'provider', text: 'Hello, I can see you. How are you feeling today?', timestamp: new Date() },
    { id: '2', sender: 'patient', text: 'I have been having headaches for the past week.', timestamp: new Date() },
  ]);
  const [newMessage, setNewMessage] = useState('');
  const [showChat, setShowChat] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 1500);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = () => {
    if (!newMessage.trim()) return;
    setMessages((prev) => [...prev, { id: Date.now().toString(), sender: 'provider', text: newMessage, timestamp: new Date() }]);
    setNewMessage('');
  };

  const endCall = () => {
    setSessionActive(false);
    toast.info('Call ended');
    setTimeout(() => router.push('/telemedicine'), 2000);
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>;
  }

  return (
    <div className="h-[calc(100vh-2rem)] flex flex-col">
      <div className="flex items-center justify-between p-4 bg-card border-b rounded-t-lg">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/telemedicine"><ArrowLeft className="h-4 w-4" /></Link>
          </Button>
          <Avatar className="h-10 w-10">
            <AvatarFallback><User className="h-5 w-5" /></AvatarFallback>
          </Avatar>
          <div>
            <p className="font-medium">Telemedicine Session</p>
            <p className="text-xs text-muted-foreground">ID: {params.id?.slice(0, 8)}</p>
          </div>
          <Badge variant={sessionActive ? 'success' : 'secondary'}>{sessionActive ? 'Active' : 'Ended'}</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => setVideoEnabled(!videoEnabled)} title={videoEnabled ? 'Disable video' : 'Enable video'}>
            {videoEnabled ? <Video className="h-5 w-5" /> : <VideoOff className="h-5 w-5 text-red-500" />}
          </Button>
          <Button variant="outline" size="icon" onClick={() => setAudioEnabled(!audioEnabled)} title={audioEnabled ? 'Mute' : 'Unmute'}>
            {audioEnabled ? <Mic className="h-5 w-5" /> : <MicOff className="h-5 w-5 text-red-500" />}
          </Button>
          <Button variant="outline" size="icon" onClick={() => setShowChat(!showChat)} title={showChat ? 'Hide chat' : 'Show chat'}>
            <MessageSquare className="h-5 w-5" />
          </Button>
          <Button variant="destructive" size="icon" onClick={endCall} title="End call">
            <PhoneOff className="h-5 w-5" />
          </Button>
        </div>
      </div>

      <div className="flex flex-1 gap-4 p-4 overflow-hidden">
        <div className={`flex-1 bg-muted rounded-lg flex items-center justify-center ${!sessionActive ? 'opacity-50' : ''}`}>
          {sessionActive ? (
            <div className="text-center">
              <Video className="h-16 w-16 mx-auto mb-3 text-muted-foreground" />
              <p className="text-lg font-medium">Video Feed</p>
              <p className="text-sm text-muted-foreground">Camera {videoEnabled ? 'active' : 'disabled'}</p>
            </div>
          ) : (
            <div className="text-center">
              <PhoneOff className="h-16 w-16 mx-auto mb-3 text-red-400" />
              <p className="text-lg font-medium">Session Ended</p>
            </div>
          )}
        </div>

        {showChat && (
          <Card className="w-80 flex flex-col">
            <CardHeader className="p-3 border-b">
              <CardTitle className="text-sm flex items-center gap-2"><MessageSquare className="h-4 w-4" />Chat</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-3 space-y-3">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.sender === 'provider' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] p-2 rounded-lg text-sm ${msg.sender === 'provider' ? 'bg-healthcare-blue text-white' : 'bg-muted'}`}>
                    <p>{msg.text}</p>
                    <p className="text-xs opacity-70 mt-1">{msg.timestamp.toLocaleTimeString()}</p>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </CardContent>
            <div className="p-3 border-t flex gap-2">
              <Textarea
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Type a message..."
                className="min-h-0 h-9 text-sm resize-none"
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              />
              <Button size="sm" onClick={sendMessage}>Send</Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
