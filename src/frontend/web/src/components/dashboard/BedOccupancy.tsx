'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Building2 } from 'lucide-react';
import type { BedOccupancy as BedOccupancyType } from '@/types';

interface BedOccupancyProps {
  data: BedOccupancyType[];
  isLoading?: boolean;
}

export function BedOccupancy({ data, isLoading }: BedOccupancyProps) {
  const overallOccupancy = data.length > 0
    ? Math.round((data.reduce((s, d) => s + d.occupied_beds, 0) / data.reduce((s, d) => s + d.total_beds, 0)) * 100)
    : 0;

  const getOccupancyColor = (rate: number) => {
    if (rate >= 90) return 'bg-red-500';
    if (rate >= 75) return 'bg-amber-500';
    return 'bg-green-500';
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Building2 className="h-5 w-5" />Bed Occupancy</CardTitle></CardHeader>
        <CardContent><div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => (<div key={i} className="h-12 bg-muted animate-pulse rounded" />))}</div></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Building2 className="h-5 w-5 text-healthcare-blue" />
          Bed Occupancy
        </CardTitle>
        <span className={`text-lg font-bold ${overallOccupancy >= 90 ? 'text-red-500' : overallOccupancy >= 75 ? 'text-amber-500' : 'text-green-500'}`}>
          {overallOccupancy}%
        </span>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium">Overall</span>
              <span className="text-muted-foreground">{data.reduce((s, d) => s + d.occupied_beds, 0)} / {data.reduce((s, d) => s + d.total_beds, 0)} beds</span>
            </div>
            <Progress value={overallOccupancy} className="h-2" indicatorClassName={getOccupancyColor(overallOccupancy)} />
          </div>
          {data.map((dept) => (
            <div key={dept.department}>
              <div className="flex justify-between text-sm mb-1">
                <span>{dept.department}</span>
                <span className="text-muted-foreground">{dept.occupied_beds} / {dept.total_beds}</span>
              </div>
              <Progress value={dept.occupancy_rate} className="h-1.5" indicatorClassName={getOccupancyColor(dept.occupancy_rate)} />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
