'use client';

import { useEffect, useState } from 'react';
import { Loader2, LogOut } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import { useCloseJourney } from '@/hooks/usePatientFlow';
import type { FlowStepOutcome } from '@/types';

interface CloseJourneyDialogProps {
  journeyId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClosed?: () => void;
}

const outcomeOptions: { value: FlowStepOutcome; label: string }[] = [
  { value: 'completed', label: 'Visit completed' },
  { value: 'discharged', label: 'Discharged' },
  { value: 'left_without_being_seen', label: 'Left without being seen' },
  { value: 'no_show', label: 'No show' },
  { value: 'cancelled', label: 'Cancelled' },
];

export function CloseJourneyDialog({
  journeyId,
  open,
  onOpenChange,
  onClosed,
}: CloseJourneyDialogProps) {
  const [outcome, setOutcome] = useState<FlowStepOutcome>('completed');
  const [reason, setReason] = useState('');
  const closeJourney = useCloseJourney(journeyId);

  useEffect(() => {
    if (!open) return;
    setOutcome('completed');
    setReason('');
  }, [open]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      await closeJourney.mutateAsync({
        outcome,
        reason: reason || undefined,
      });
      toast.success('Journey closed');
      onOpenChange(false);
      onClosed?.();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to close journey');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <LogOut className="h-5 w-5 text-healthcare-blue" />
            Close journey
          </DialogTitle>
          <DialogDescription>
            End this visit. Any open step will be closed and the patient removed from the queue.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Outcome *</label>
            <Select value={outcome} onValueChange={(value) => setOutcome(value as FlowStepOutcome)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {outcomeOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Reason / note</label>
            <Input
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Optional note for the record"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" disabled={closeJourney.isPending}>
              {closeJourney.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Close journey
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
