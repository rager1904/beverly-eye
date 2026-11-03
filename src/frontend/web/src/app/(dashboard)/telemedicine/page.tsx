'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { VideoCall } from '@/components/telemedicine/VideoCall';
import { WaitingRoom } from '@/components/telemedicine/WaitingRoom';
import { useAuthStore } from '@/lib/auth';
import { Video, Users, Clock, History, Calendar, Loader2 } from 'lucide-react';
import { AiChatWidget } from '@/components/patient/AiChatWidget';
import { formatDateTime } from '@/lib/utils';

interface Session {
  id: string;
  patient_id: string;
  provider_id: string;
  status: 'waiting' | 'active' | 'completed' | 'missed';
  start_time?: string;
  end_time?: string;
  signal_quality?: 'excellent' | 'good' | 'fair' | 'poor';
  patient_name?: string;
  provider_name?: string;
  notes?: string;
}

export default function TelemedicinePage() {
  const user = useAuthStore((s) => s.user);
  const [activeCall, setActiveCall] = useState<string | null>(null);
  const [showCall, setShowCall] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  const token = useAuthStore((s) => s.accessToken);

  const fetchSessions = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    setLoading(true);
    try {
      const res = await fetch('/api/v1/appointments?appointment_type=telemedicine&per_page=20', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data.items || data.data || data.appointments || []);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchSessions(); }, [fetchSessions]);

  const handleStartCall = (sessionId: string) => {
    setActiveCall(sessionId);
    setShowCall(true);
  };

  if (showCall && activeCall) {
    return (
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <h1 className="text-xl sm:text-2xl font-bold flex items-center gap-2">
            <Video className="h-5 w-6 sm:h-6 sm:w-6 text-healthcare-blue shrink-0" />Telemedicine Call
          </h1>
          <Button variant="outline" size="sm" onClick={() => setShowCall(false)}>End &amp; Return</Button>
        </div>
        <VideoCall
          sessionId={activeCall}
          participantName="Patient"
          participantRole="Patient"
          onEnd={() => setShowCall(false)}
        />
      </div>
    );
  }

  const waiting = sessions.filter((s) => s.status === 'waiting');
  const active = sessions.filter((s) => s.status === 'active');
  const history = sessions.filter((s) => s.status === 'completed' || s.status === 'missed');

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold flex items-center gap-2">
            <Video className="h-5 w-6 sm:h-6 sm:w-6 text-healthcare-blue shrink-0" />
            Telemedicine Portal
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground">Virtual healthcare consultations across Zambia</p>
        </div>
        <Badge variant="success" className="flex items-center gap-1 self-start sm:self-center">
          <div className="w-2 h-2 rounded-full bg-green-500" />Online
        </Badge>
      </div>

      <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Available Providers', value: user ? 'Online' : 'N/A', icon: Users, color: 'text-green-600 bg-green-100' },
          { label: 'In Queue', value: waiting.length.toString(), icon: Clock, color: 'text-amber-600 bg-amber-100' },
          { label: 'Active Calls', value: active.length.toString(), icon: Video, color: 'text-blue-600 bg-blue-100' },
          { label: "Today's Sessions", value: sessions.length.toString(), icon: Calendar, color: 'text-purple-600 bg-purple-100' },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardContent className="p-3 sm:p-4 flex items-center gap-3 sm:gap-4">
              <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-lg ${color} flex items-center justify-center shrink-0`}>
                <Icon className="h-5 w-5 sm:h-6 sm:w-6" />
              </div>
              <div className="min-w-0">
                <p className="text-lg sm:text-2xl font-bold">{value}</p>
                <p className="text-xs text-muted-foreground truncate">{label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="waiting">
        <TabsList className="flex-wrap">
          <TabsTrigger value="waiting" className="text-xs sm:text-sm"><Clock className="h-3 w-4 sm:h-4 sm:w-4 mr-1" />Waiting ({waiting.length})</TabsTrigger>
          <TabsTrigger value="active" className="text-xs sm:text-sm"><Video className="h-3 w-4 sm:h-4 sm:w-4 mr-1" />Active ({active.length})</TabsTrigger>
          <TabsTrigger value="scheduled" className="text-xs sm:text-sm"><Calendar className="h-3 w-4 sm:h-4 sm:w-4 mr-1" />Scheduled</TabsTrigger>
          <TabsTrigger value="history" className="text-xs sm:text-sm"><History className="h-3 w-4 sm:h-4 sm:w-4 mr-1" />History ({history.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="waiting">
          {loading ? (
            <div className="flex items-center justify-center h-24"><Loader2 className="h-5 w-5 animate-spin" /></div>
          ) : waiting.length === 0 ? (
            <Card><CardContent className="text-center py-6 sm:py-8 text-muted-foreground">
              <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No patients waiting</p>
            </CardContent></Card>
          ) : (
            <WaitingRoom sessions={waiting} onStartCall={handleStartCall} />
          )}
        </TabsContent>

        <TabsContent value="active">
          {loading ? (
            <div className="flex items-center justify-center h-24"><Loader2 className="h-5 w-5 animate-spin" /></div>
          ) : active.length === 0 ? (
            <Card><CardContent className="text-center py-6 sm:py-8 text-muted-foreground">
              <Video className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No active calls</p>
            </CardContent></Card>
          ) : (
            <Card>
              <CardHeader className="p-3 sm:p-4"><CardTitle className="text-sm sm:text-lg">Active Teleconsultations</CardTitle></CardHeader>
              <CardContent className="p-3 sm:p-4">
                <div className="space-y-2 sm:space-y-3">
                  {active.map((session) => (
                    <div key={session.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-3 sm:p-4 rounded-lg border border-green-200 bg-green-50 gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shrink-0" />
                          <span className="font-medium text-sm truncate">{session.patient_name || `Patient #${session.patient_id?.slice(0, 6)}`}</span>
                          <Badge variant="success" className="text-xs">In Progress</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {session.start_time && `Started ${formatDateTime(session.start_time)}`}
                          {session.provider_name && ` | ${session.provider_name}`}
                        </p>
                      </div>
                      <Button size="sm" className="bg-healthcare-green hover:bg-healthcare-green-dark self-end sm:self-center" onClick={() => handleStartCall(session.id)}>
                        <Video className="h-4 w-4 mr-1" />Join
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="scheduled">
          <Card>
            <CardHeader className="p-3 sm:p-4"><CardTitle className="text-sm sm:text-lg">Scheduled Appointments</CardTitle></CardHeader>
            <CardContent className="p-3 sm:p-4">
              <p className="text-sm text-muted-foreground text-center py-6">No upcoming scheduled telemedicine appointments</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history">
          {loading ? (
            <div className="flex items-center justify-center h-24"><Loader2 className="h-5 w-5 animate-spin" /></div>
          ) : history.length === 0 ? (
            <Card><CardContent className="text-center py-6 sm:py-8 text-muted-foreground">
              <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No session history</p>
            </CardContent></Card>
          ) : (
            <Card>
              <CardHeader className="p-3 sm:p-4"><CardTitle className="text-sm sm:text-lg">Session History</CardTitle></CardHeader>
              <CardContent className="p-3 sm:p-4">
                <div className="space-y-2 sm:space-y-3">
                  {history.map((session) => (
                    <div key={session.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-3 rounded-lg border gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-sm">{session.patient_name || `Patient #${session.patient_id?.slice(0, 6)}`}</span>
                          <Badge variant={session.status === 'completed' ? 'success' : 'critical'} className="text-xs">{session.status}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">{session.start_time ? formatDateTime(session.start_time) : 'N/A'}</p>
                        {session.notes && <p className="text-xs text-muted-foreground mt-1">{session.notes}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
      <AiChatWidget open={chatOpen} onOpenChange={setChatOpen} />
    </div>
  );
}
