'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, UserPlus, Loader2, Stethoscope } from 'lucide-react';
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
import { Badge } from '@/components/ui/badge';
import {
  useFlowDestinations,
  usePatientSearch,
  useStartJourney,
} from '@/hooks/usePatientFlow';
import type {
  DestinationStaff,
  FlowStepType,
  JourneyPriority,
  PatientSearchResult,
  PaymentScheme,
  VisitPaymentStatus,
  VisitType,
} from '@/types';

interface StartJourneyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const priorityOptions: { value: JourneyPriority; label: string }[] = [
  { value: 'routine', label: 'Routine' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'emergency', label: 'Emergency' },
];

const paymentSchemes: { value: PaymentScheme; label: string }[] = [
  { value: 'cash', label: 'Cash' },
  { value: 'nhima', label: 'NHIMA' },
  { value: 'prudential', label: 'Prudential' },
  { value: 'sanlam', label: 'Sanlam' },
  { value: 'madison', label: 'Madison' },
  { value: 'jubilee', label: 'Jubilee' },
  { value: 'employer', label: 'Employer scheme' },
  { value: 'other', label: 'Other' },
];

export function StartJourneyDialog({ open, onOpenChange }: StartJourneyDialogProps) {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [patient, setPatient] = useState<PatientSearchResult | null>(null);
  const [priority, setPriority] = useState<JourneyPriority>('routine');
  const [paymentScheme, setPaymentScheme] = useState<PaymentScheme>('cash');
  const [visitType, setVisitType] = useState<VisitType>('new');
  const [paymentStatus, setPaymentStatus] = useState<VisitPaymentStatus>('unpaid');
  const [schemeNumber, setSchemeNumber] = useState('');
  const [servicePoint, setServicePoint] = useState('general');
  const [departmentId, setDepartmentId] = useState('');
  const [providerId, setProviderId] = useState('');
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [reason, setReason] = useState('');

  const { data: results, isFetching: searching } = usePatientSearch(search);
  const { data: destinations, isLoading: destinationsLoading } = useFlowDestinations();
  const startJourney = useStartJourney();

  const selectedServicePoint = destinations?.service_points.find(
    (point) => point.code === servicePoint
  );

  const staffOptions = useMemo<DestinationStaff[]>(() => {
    const staff = destinations?.staff ?? [];
    if (!departmentId) return staff;
    return staff.filter((member) => member.department_id === departmentId);
  }, [destinations?.staff, departmentId]);

  const reset = () => {
    setSearch('');
    setPatient(null);
    setPriority('routine');
    setPaymentScheme('cash');
    setVisitType('new');
    setPaymentStatus('unpaid');
    setSchemeNumber('');
    setServicePoint('general');
    setDepartmentId('');
    setProviderId('');
    setChiefComplaint('');
    setReason('');
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  const choosePatient = (selected: PatientSearchResult) => {
    setPatient(selected);
    setSearch('');
  };

  const chooseProvider = (value: string) => {
    setProviderId(value);
    const member = destinations?.staff.find((item) => item.id === value);
    if (member?.department_id) setDepartmentId(member.department_id);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!patient) {
      toast.error('Select the patient who has arrived');
      return;
    }

    const department = destinations?.departments.find((item) => item.id === departmentId);
    const provider = destinations?.staff.find((item) => item.id === providerId);

    try {
      const journey = await startJourney.mutateAsync({
        patient_id: patient.id,
        priority,
        payment_scheme: paymentScheme,
        visit_type: visitType,
        payment_status: paymentStatus,
        scheme_number: schemeNumber || undefined,
        chief_complaint: chiefComplaint || undefined,
        step_type: (selectedServicePoint?.step_type ?? servicePoint) as FlowStepType,
        service_point: selectedServicePoint?.code ?? servicePoint,
        department_id: department?.id,
        department_name: department?.name,
        provider_id: provider?.user_id || provider?.id,
        provider_name: provider?.name,
        reason: reason || undefined,
      });
      toast.success(`Journey ${journey.journey_number} started`);
      handleOpenChange(false);
      router.push(`/patient-flow/${journey.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to start journey');
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="h-5 w-5 text-healthcare-green" />
            Check in patient
          </DialogTitle>
          <DialogDescription>
            Start a visit and route the patient to a counter, department and clinician.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Patient *</label>
            {patient ? (
              <div className="flex items-center justify-between rounded-md border bg-muted/40 px-3 py-2">
                <div>
                  <p className="text-sm font-medium">
                    {patient.first_name} {patient.last_name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {patient.nrc_number || 'No NRC'} · {patient.phone || 'No phone'}
                  </p>
                </div>
                <Button type="button" variant="ghost" size="sm" onClick={() => setPatient(null)}>
                  Change
                </Button>
              </div>
            ) : (
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search by name, NRC or phone..."
                  className="pl-9"
                  autoFocus
                />
                {search.trim().length >= 2 && (
                  <div className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-md border bg-popover shadow-lg">
                    {searching ? (
                      <div className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" /> Searching...
                      </div>
                    ) : results?.items.length ? (
                      results.items.map((result) => (
                        <button
                          key={result.id}
                          type="button"
                          onClick={() => choosePatient(result)}
                          className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-accent"
                        >
                          <span>
                            {result.first_name} {result.last_name}
                            <span className="ml-2 text-xs text-muted-foreground">
                              {result.nrc_number || result.phone}
                            </span>
                          </span>
                          <Badge variant="outline">{result.gender}</Badge>
                        </button>
                      ))
                    ) : (
                      <p className="px-3 py-2 text-sm text-muted-foreground">No patients found</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Payment scheme</label>
              <Select value={paymentScheme} onValueChange={(value) => setPaymentScheme(value as PaymentScheme)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {paymentSchemes.map((scheme) => (
                    <SelectItem key={scheme.value} value={scheme.value}>
                      {scheme.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Visit type</label>
              <Select value={visitType} onValueChange={(value) => setVisitType(value as VisitType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="new">New visit</SelectItem>
                  <SelectItem value="review">Review</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Payment status</label>
              <Select
                value={paymentStatus}
                onValueChange={(value) => setPaymentStatus(value as VisitPaymentStatus)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="paid">Paid</SelectItem>
                  <SelectItem value="unpaid">Unpaid</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {paymentScheme !== 'cash' && (
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {paymentScheme === 'nhima' ? 'NHIMA number' : 'Scheme / member number'}
              </label>
              <Input
                value={schemeNumber}
                onChange={(event) => setSchemeNumber(event.target.value)}
                placeholder={
                  paymentScheme === 'nhima'
                    ? 'NHIMA membership number'
                    : 'Policy or member number'
                }
              />
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Priority</label>
              <Select value={priority} onValueChange={(value) => setPriority(value as JourneyPriority)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {priorityOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Send to service point *</label>
              <Select value={servicePoint} onValueChange={setServicePoint}>
                <SelectTrigger>
                  <SelectValue placeholder={destinationsLoading ? 'Loading...' : 'Select service point'} />
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
            <label className="text-sm font-medium">Chief complaint</label>
            <Textarea
              value={chiefComplaint}
              onChange={(event) => setChiefComplaint(event.target.value)}
              placeholder="Why has the patient come in today?"
              rows={2}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Routing note</label>
            <Input
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Optional note for the receiving desk"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={startJourney.isPending || !patient}>
              {startJourney.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Start journey
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
