'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { MessageSquare, X, Send, Bot, User, Loader2, Mic, MicOff, Volume2, VolumeX } from 'lucide-react';
import { useAuthStore } from '@/lib/auth';
import { useTts } from '@/hooks/useTts';
import { useAsr } from '@/hooks/useAsr';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const QUICK_ACTIONS = [
  'What medications am I taking?',
  'Explain my lab results',
  'Health tips for malaria prevention',
  'When is my next appointment?',
];

interface AiChatWidgetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AiChatWidget({ open, onOpenChange }: AiChatWidgetProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'Hello! I\'m your UbuntuCare health assistant. Ask me about your medications, appointments, lab results, or get health tips.' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const token = useAuthStore((s) => s.accessToken);
  const { speak, stop: stopTts, isSpeaking } = useTts();
  const [speakingIndex, setSpeakingIndex] = useState<number | null>(null);
  const [micHover, setMicHover] = useState(false);

  const { startListening, stopListening, isListening, isTranscribing } = useAsr((text) => {
    setInput(text);
  });

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!isSpeaking) setSpeakingIndex(null);
  }, [isSpeaking]);

  async function sendMessage(message: string) {
    if (!message.trim()) return;
    setMessages((prev) => [...prev, { role: 'user', content: message }]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(err.error || err.detail || 'Failed to get response');
      }

      const data = await res.json();
      setConversationId(data.conversation_id);
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response || data.message || 'No response' }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: err instanceof Error ? err.message : 'Connection error. Please try again.' }]);
    } finally {
      setLoading(false);
    }
  }

  function handleSpeak(text: string, index: number) {
    if (isSpeaking && speakingIndex === index) {
      stopTts();
    } else {
      setSpeakingIndex(index);
      speak(text);
    }
  }

  async function handleMicPointerDown() {
    await startListening();
  }

  function handleMicPointerUp() {
    stopListening();
  }

  return (
    <>
      {!open && (
        <div className="fixed bottom-6 right-6 z-50">
          <Button
            onClick={() => onOpenChange(true)}
            className="h-14 w-14 rounded-full shadow-lg bg-healthcare-green hover:bg-healthcare-green-dark"
          >
            <MessageSquare className="h-6 w-6" />
          </Button>
        </div>
      )}

      {open && (
        <div className="fixed bottom-4 left-4 right-4 z-50 ml-auto max-w-[400px] sm:bottom-6 sm:left-auto sm:right-6 sm:w-[400px]">
          <Card className="max-h-[calc(100dvh-2rem)] overflow-y-auto border-2 shadow-2xl sm:max-h-[calc(100dvh-3rem)]">
            <CardHeader className="flex flex-row items-center justify-between p-4 bg-healthcare-green text-white rounded-t-lg">
              <CardTitle className="text-sm flex items-center gap-2">
                <Bot className="h-5 w-5" />
                UbuntuCare Health Assistant
              </CardTitle>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-white hover:bg-white/20" onClick={() => onOpenChange(false)}>
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>

            <CardContent className="p-0">
              <div className="h-[min(400px,45dvh)] overflow-y-auto p-4 space-y-3">
                {messages.map((msg, i) => (
                  <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                    {msg.role === 'assistant' && (
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-healthcare-green/10 flex items-center justify-center">
                        <Bot className="h-4 w-4 text-healthcare-green" />
                      </div>
                    )}
                    <div className={`min-w-0 max-w-[80%] break-words rounded-lg px-3 py-2 text-sm ${
                      msg.role === 'user' ? 'bg-healthcare-green text-white' : 'bg-muted'
                    }`}>
                      {msg.content}
                    </div>
                    {msg.role === 'user' && (
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                        <User className="h-4 w-4 text-blue-600" />
                      </div>
                    )}
                    {msg.role === 'assistant' && (
                      <button
                        onClick={() => handleSpeak(msg.content, i)}
                        className="flex-shrink-0 w-8 h-8 rounded-full bg-muted hover:bg-accent flex items-center justify-center transition-colors"
                        title={isSpeaking && speakingIndex === i ? 'Stop' : 'Read aloud'}
                      >
                        {isSpeaking && speakingIndex === i ? (
                          <VolumeX className="h-4 w-4 text-healthcare-green" />
                        ) : (
                          <Volume2 className="h-4 w-4 text-muted-foreground" />
                        )}
                      </button>
                    )}
                  </div>
                ))}
                {loading && (
                  <div className="flex gap-2">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-healthcare-green/10 flex items-center justify-center"><Bot className="h-4 w-4 text-healthcare-green" /></div>
                    <div className="bg-muted rounded-lg px-3 py-2"><Loader2 className="h-4 w-4 animate-spin" /></div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {messages.length === 1 && (
                <div className="px-4 pb-2">
                  <p className="text-xs text-muted-foreground mb-2">Quick questions:</p>
                  <div className="flex flex-wrap gap-2">
                    {QUICK_ACTIONS.map((action) => (
                      <button
                        key={action}
                        onClick={() => sendMessage(action)}
                        className="text-xs bg-muted hover:bg-accent rounded-full px-3 py-1.5 transition-colors text-left"
                      >
                        {action}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="p-4 pt-2 border-t">
                <form onSubmit={(e) => { e.preventDefault(); sendMessage(input); }} className="flex gap-2">
                  <Input
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about your health..."
                    disabled={loading}
                    className="flex-1"
                  />
                  {input.trim() ? (
                    <Button type="submit" size="icon" disabled={loading || !input.trim()}>
                      <Send className="h-4 w-4" />
                    </Button>
                  ) : (
                    <div className="relative">
                      {isTranscribing && (
                        <div className="absolute -top-1 -right-1 w-3 h-3">
                          <Loader2 className="h-3 w-3 animate-spin text-healthcare-green" />
                        </div>
                      )}
                      <Button
                        type="button"
                        size="icon"
                        variant={isListening ? 'destructive' : 'outline'}
                        onPointerDown={handleMicPointerDown}
                        onPointerUp={handleMicPointerUp}
                        onPointerLeave={isListening ? handleMicPointerUp : undefined}
                        onMouseEnter={() => setMicHover(true)}
                        onMouseLeave={() => setMicHover(false)}
                        disabled={loading}
                        className={isListening ? 'animate-pulse' : ''}
                        title={isListening ? 'Release to stop recording' : 'Hold to record'}
                      >
                        {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                      </Button>
                      {isListening && (
                        <span className="absolute -top-1 -right-1 flex h-3 w-3">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                          <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
                        </span>
                      )}
                    </div>
                  )}
                </form>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
