'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Clock, User, Loader2, Video } from 'lucide-react';
import { getInitials, formatTime } from '@/lib/utils';
import type { TelemedicineSession } from '@/types';

interface WaitingRoomProps {
  sessions: TelemedicineSession[];
  onStartCall: (sessionId: string) => void;
  isLoading?: boolean;
}

export function WaitingRoom({ sessions, onStartCall, isLoading }: WaitingRoomProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Clock className="h-5 w-5" />Waiting Room</CardTitle></CardHeader>
        <CardContent><div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => (<div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />))}</div></CardContent>
      </Card>
    );
  }

  const waitingSessions = sessions.filter((s) => s.status === 'waiting');

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Clock className="h-5 w-5 text-healthcare-blue" />
          Waiting Room
        </CardTitle>
        <Badge>{waitingSessions.length} waiting</Badge>
      </CardHeader>
      <CardContent>
        {waitingSessions.length === 0 ? (
          <div className="text-center py-8">
            <User className="h-12 w-12 text-muted-foreground mx-auto mb-3 opacity-50" />
            <p className="text-sm text-muted-foreground">No patients waiting</p>
          </div>
        ) : (
          <div className="space-y-3">
            {waitingSessions.map((session) => (
              <div key={session.id} className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent/50 transition-colors">
                <div className="flex items-center gap-3">
                  <Avatar>
                    <AvatarFallback className="bg-healthcare-green/10 text-healthcare-green">{getInitials('Patient')}</AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="font-medium">Patient #{session.patient_id.slice(0, 8)}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {session.start_time ? formatTime(session.start_time) : 'Waiting'}
                      <span className="flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" />Checking vitals</span>
                    </div>
                  </div>
                </div>
                <Button size="sm" className="bg-healthcare-green hover:bg-healthcare-green-dark" onClick={() => onStartCall(session.id)}>
                  <Video className="h-4 w-4 mr-1" />Start Call
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
