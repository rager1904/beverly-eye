'use client';

import { useEffect, useMemo, useState } from 'react';
import { Loader2, Send, Stethoscope } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useFlowDestinations, useRoutePatient } from '@/hooks/usePatientFlow';
import type { DestinationStaff, FlowStepType, JourneyPriority } from '@/types';

interface RoutePatientDialogProps {
  journeyId: string;
  facilityId?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentServicePoint?: string | null;
  onRouted?: () => void;
}

const priorityOptions: { value: JourneyPriority; label: string }[] = [
  { value: 'routine', label: 'Routine' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'emergency', label: 'Emergency' },
];

export function RoutePatientDialog({
  journeyId,
  facilityId,
  open,
  onOpenChange,
  currentServicePoint,
  onRouted,
}: RoutePatientDialogProps) {
  const [servicePoint, setServicePoint] = useState('consultation');
  const [departmentId, setDepartmentId] = useState('');
  const [providerId, setProviderId] = useState('');
  const [priority, setPriority] = useState<JourneyPriority | 'keep'>('keep');
  const [reason, setReason] = useState('');
  const [notes, setNotes] = useState('');

  const { data: destinations } = useFlowDestinations(facilityId);
  const routePatient = useRoutePatient(journeyId, facilityId);

  useEffect(() => {
    if (!open) return;
    // Onward referral defaults to the next logical desk: a consultation room
    // returns to the lab/pharmacy, while every other point returns to a doctor.
    setServicePoint(currentServicePoint === 'consultation' ? 'laboratory' : 'consultation');
    setDepartmentId('');
    setProviderId('');
    setPriority('keep');
    setReason('');
    setNotes('');
  }, [open, currentServicePoint]);

  const selectedServicePoint = destinations?.service_points.find(
    (point) => point.code === servicePoint
  );

  const staffOptions = useMemo<DestinationStaff[]>(() => {
    const staff = destinations?.staff ?? [];
    if (!departmentId) return staff;
    return staff.filter((member) => member.department_id === departmentId);
  }, [destinations?.staff, departmentId]);

  const chooseProvider = (value: string) => {
    setProviderId(value);
    const member = destinations?.staff.find((item) => item.id === value);
    if (member?.department_id) setDepartmentId(member.department_id);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const department = destinations?.departments.find((item) => item.id === departmentId);
    const provider = destinations?.staff.find((item) => item.id === providerId);

    try {
      await routePatient.mutateAsync({
        step_type: (selectedServicePoint?.step_type ?? servicePoint) as FlowStepType,
        service_point: selectedServicePoint?.code ?? servicePoint,
        department_id: department?.id,
        department_name: department?.name,
        provider_id: provider?.user_id || provider?.id,
        provider_name: provider?.name,
        priority: priority === 'keep' ? undefined : priority,
        reason: reason || undefined,
        notes: notes || undefined,
        outcome: 'referred',
      });
      toast.success('Patient sent onward');
      onOpenChange(false);
      onRouted?.();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to route patient');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Send className="h-5 w-5 text-healthcare-blue" />
            Send patient onward
          </DialogTitle>
          <DialogDescription>
            Refer the patient to another doctor, counter, nurse or service point.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Destination *</label>
            <Select value={servicePoint} onValueChange={setServicePoint}>
              <SelectTrigger>
                <SelectValue placeholder="Select destination" />
              </SelectTrigger>
              <SelectContent>
                {(destinations?.service_points ?? []).map((point) => (
                  <SelectItem key={point.code} value={point.code}>
                    {point.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Department</label>
              <Select
                value={departmentId || 'none'}
                onValueChange={(value) => {
                  setDepartmentId(value === 'none' ? '' : value);
                  setProviderId('');
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Any department" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Any department</SelectItem>
                  {(destinations?.departments ?? []).map((department) => (
                    <SelectItem key={department.id} value={department.id}>
                      {department.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Doctor / nurse</label>
              <Select value={providerId || 'none'} onValueChange={(value) => chooseProvider(value === 'none' ? '' : value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Any available clinician" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Any available clinician</SelectItem>
                  {staffOptions.map((member) => (
                    <SelectItem key={member.id} value={member.id}>
                      <span className="flex items-center gap-2">
                        <Stethoscope className="h-3.5 w-3.5" />
                        {member.name} · {member.role.replace('_', ' ')}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Priority</label>
            <Select value={priority} onValueChange={(value) => setPriority(value as JourneyPriority | 'keep')}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="keep">Keep current priority</SelectItem>
                {priorityOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Reason for referral</label>
            <Input
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="e.g. Needs full blood count"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Notes for receiving team</label>
            <Textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={2}
              placeholder="Optional clinical or administrative note"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={routePatient.isPending}>
              {routePatient.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Send patient
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
