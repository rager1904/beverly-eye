'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export function FacilitySelect({ value, onChange, disabled }: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const facilities = useQuery({
    queryKey: ['active-facilities'],
    queryFn: () => api.get<{ id: string; name: string; code: string }[]>('/hospital/list'),
  });

  return (
    <div className="space-y-1">
      <label htmlFor="registration-facility" className="text-sm font-medium">Facility</label>
      <Select value={value} onValueChange={onChange} disabled={disabled || facilities.isPending || facilities.isError}>
        <SelectTrigger id="registration-facility">
          <SelectValue placeholder="Select a facility" />
        </SelectTrigger>
        <SelectContent>
          {facilities.data?.map((facility) => (
            <SelectItem key={facility.id} value={facility.id}>
              {facility.name} ({facility.code})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {facilities.isError && <p role="alert" className="text-sm text-destructive">Could not load facilities.</p>}
      {facilities.data?.length === 0 && <p className="text-sm text-muted-foreground">No active facilities are available.</p>}
    </div>
  );
}
