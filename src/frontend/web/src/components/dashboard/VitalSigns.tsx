'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, Heart, Thermometer, Wind, Droplets } from 'lucide-react';
import type { VitalSign } from '@/types';

interface VitalSignsProps {
  vitals: VitalSign | VitalSign[];
  isLoading?: boolean;
  title?: string;
}

const vitalConfig = [
  { key: 'blood_pressure_systolic', label: 'BP Systolic', unit: 'mmHg', icon: Activity, normal: { min: 90, max: 140 } },
  { key: 'blood_pressure_diastolic', label: 'BP Diastolic', unit: 'mmHg', icon: Activity, normal: { min: 60, max: 90 } },
  { key: 'heart_rate', label: 'Heart Rate', unit: 'bpm', icon: Heart, normal: { min: 60, max: 100 } },
  { key: 'respiratory_rate', label: 'Resp Rate', unit: '/min', icon: Wind, normal: { min: 12, max: 20 } },
  { key: 'temperature', label: 'Temperature', unit: '°C', icon: Thermometer, normal: { min: 36.0, max: 37.5 } },
  { key: 'oxygen_saturation', label: 'SpO₂', unit: '%', icon: Droplets, normal: { min: 95, max: 100 } },
];

export function VitalSigns({ vitals, isLoading, title = 'Vital Signs' }: VitalSignsProps) {
  const latestVitals = Array.isArray(vitals) ? vitals[0] : vitals;

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Activity className="h-5 w-5" />{title}</CardTitle></CardHeader>
        <CardContent><div className="grid grid-cols-3 gap-3">{Array.from({ length: 6 }).map((_, i) => (<div key={i} className="h-20 bg-muted animate-pulse rounded-lg" />))}</div></CardContent>
      </Card>
    );
  }

  if (!latestVitals) {
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Activity className="h-5 w-5" />{title}</CardTitle></CardHeader>
        <CardContent><p className="text-sm text-muted-foreground text-center py-8">No vital signs recorded</p></CardContent>
      </Card>
    );
  }

  const getValue = (vital: VitalSign, key: string): number | null => {
    switch (key) {
      case 'blood_pressure_systolic': return vital.blood_pressure_systolic;
      case 'blood_pressure_diastolic': return vital.blood_pressure_diastolic;
      case 'heart_rate': return vital.heart_rate;
      case 'respiratory_rate': return vital.respiratory_rate;
      case 'temperature': return vital.temperature;
      case 'oxygen_saturation': return vital.oxygen_saturation;
      default: return null;
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Activity className="h-5 w-5 text-healthcare-blue" />
          {title}
        </CardTitle>
        <Badge variant="outline" className="text-xs">{new Date(latestVitals.recorded_at).toLocaleTimeString()}</Badge>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-3">
          {vitalConfig.map(({ key, label, unit, icon: Icon, normal }) => {
            const value = getValue(latestVitals, key);
            if (value === null) return null;
            const isAbnormal = value < normal.min || value > normal.max;
            return (
              <div key={key} className={`p-3 rounded-lg border ${isAbnormal ? 'bg-red-50 border-red-200' : 'bg-card'}`}>
                <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                  <Icon className={`h-3 w-3 ${isAbnormal ? 'text-red-500' : ''}`} />
                  {label}
                </div>
                <div className={`text-lg font-bold ${isAbnormal ? 'text-red-600' : ''}`}>
                  {value}{unit}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
