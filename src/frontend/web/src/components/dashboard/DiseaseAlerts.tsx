'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, MapPin, TrendingUp, ChevronDown, ChevronUp } from 'lucide-react';
import type { DiseaseAlert } from '@/types';

interface DiseaseAlertsProps {
  alerts: DiseaseAlert[];
  isLoading?: boolean;
}

const severityColors: Record<string, string> = {
  low: 'bg-green-100 text-green-800',
  moderate: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
};

const severityIcons: Record<string, string> = {
  low: '🟢',
  moderate: '🟡',
  high: '🟠',
  critical: '🔴',
};

export function DiseaseAlerts({ alerts, isLoading }: DiseaseAlertsProps) {
  const [expanded, setExpanded] = useState(false);
  const displayAlerts = expanded ? alerts : alerts.slice(0, 3);

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5" />Disease Alerts</CardTitle></CardHeader>
        <CardContent><div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => (<div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />))}</div></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-lg">
          <AlertTriangle className="h-5 w-5 text-red-500" />
          Disease Surveillance
        </CardTitle>
        {alerts.filter((a) => a.severity === 'critical' || a.severity === 'high').length > 0 && (
          <Badge variant="critical">{alerts.filter((a) => a.severity === 'critical' || a.severity === 'high').length} active</Badge>
        )}
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {displayAlerts.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No active disease alerts</p>
          ) : (
            displayAlerts.map((alert) => (
              <div key={alert.id} className="p-3 rounded-lg border bg-card">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span>{severityIcons[alert.severity]}</span>
                    <span className="font-medium">{alert.disease}</span>
                    <Badge variant="outline" className={`text-xs ${severityColors[alert.severity]}`}>{alert.severity}</Badge>
                  </div>
                  <Badge variant={alert.status === 'active' ? 'destructive' : 'outline'}>{alert.status}</Badge>
                </div>
                <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{alert.district}, {alert.province}</span>
                  <span className="flex items-center gap-1"><TrendingUp className="h-3 w-3" />{alert.cases_reported} cases</span>
                </div>
                {alert.notes && <p className="text-xs text-muted-foreground mt-1">{alert.notes}</p>}
              </div>
            ))
          )}
          {alerts.length > 3 && (
            <Button variant="ghost" size="sm" className="w-full" onClick={() => setExpanded(!expanded)}>
              {expanded ? <>Show less <ChevronUp className="h-4 w-4 ml-1" /></> : <>Show {alerts.length - 3} more <ChevronDown className="h-4 w-4 ml-1" /></>}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
