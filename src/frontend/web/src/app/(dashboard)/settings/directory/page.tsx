'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Building2,
  Loader2,
  Pencil,
  Plus,
  Stethoscope,
  Trash2,
  UserRound,
} from 'lucide-react';
import { toast } from 'sonner';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { FacilitySelect } from '@/components/FacilitySelect';
import { useAuthStore } from '@/lib/auth';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  useCreateDepartment,
  useCreateStaff,
  useDeactivateDepartment,
  useDeactivateStaff,
  useDepartments,
  useStaffDirectory,
  useUpdateDepartment,
  useUpdateStaff,
  type DepartmentInput,
  type StaffInput,
} from '@/hooks/useHospitalDirectory';
import type { HospitalDepartment, HospitalStaff, HospitalStaffRole } from '@/types';

const staffRoles: { value: HospitalStaffRole; label: string }[] = [
  { value: 'doctor', label: 'Doctor' },
  { value: 'nurse', label: 'Nurse' },
  { value: 'midwife', label: 'Midwife' },
  { value: 'clinical_officer', label: 'Clinical officer' },
  { value: 'pharmacist', label: 'Pharmacist' },
  { value: 'lab_technician', label: 'Lab technician' },
  { value: 'radiographer', label: 'Radiographer' },
  { value: 'administrator', label: 'Administrator' },
  { value: 'accountant', label: 'Accountant' },
  { value: 'records_officer', label: 'Records officer' },
  { value: 'community_health_worker', label: 'Community health worker' },
  { value: 'cleaner', label: 'Cleaner' },
  { value: 'security', label: 'Security' },
];

const emptyDepartment: DepartmentInput = {
  name: '',
  code: '',
  head_of_department: '',
  location: '',
  phone_extension: '',
};

const emptyStaff: StaffInput = {
  first_name: '',
  last_name: '',
  role: 'doctor',
  speciality: '',
  department_id: '',
  phone: '',
  email: '',
  license_number: '',
  max_hours_per_week: 40,
};

function clean<T extends object>(value: T): T {
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).filter(
      ([, item]) => item !== '' && item !== undefined && item !== null
    )
  ) as T;
}

export default function DirectoryPage() {
  const user = useAuthStore((state) => state.user);
  const isAdmin = user?.role === 'admin';
  const [facilityId, setFacilityId] = useState('');

  const currentFacility = useQuery({
    queryKey: ['directory-current-facility'],
    queryFn: () => api.get<{ id: string }>('/hospital'),
    enabled: isAdmin && !facilityId,
  });
  const accountFacility = facilityId || currentFacility.data?.id;
  const staffAccounts = useQuery({
    queryKey: ['directory-login-accounts'],
    queryFn: () => api.get<{ id: string; email: string; enabled: boolean; hospital_id: string | null }[]>('/auth/admin/users'),
    enabled: isAdmin,
  });
  const eligibleAccounts = staffAccounts.data?.filter(
    (account) => account.enabled && accountFacility && account.hospital_id === accountFacility
  ) ?? [];

  const departments = useDepartments(false, facilityId);
  const staff = useStaffDirectory(facilityId);

  const createDepartment = useCreateDepartment(facilityId);
  const updateDepartment = useUpdateDepartment(facilityId);
  const deactivateDepartment = useDeactivateDepartment(facilityId);
  const createStaff = useCreateStaff(facilityId);
  const updateStaff = useUpdateStaff(facilityId);
  const deactivateStaff = useDeactivateStaff(facilityId);

  const [departmentForm, setDepartmentForm] = useState<DepartmentInput>(emptyDepartment);
  const [editingDepartment, setEditingDepartment] = useState<HospitalDepartment | null>(null);
  const [staffForm, setStaffForm] = useState<StaffInput>(emptyStaff);
  const [editingStaff, setEditingStaff] = useState<HospitalStaff | null>(null);

  const changeFacility = (value: string) => {
    setFacilityId(value);
    setEditingDepartment(null);
    setDepartmentForm(emptyDepartment);
    setEditingStaff(null);
    setStaffForm(emptyStaff);
  };

  const activeDepartments = useMemo(
    () => (departments.data ?? []).filter((department) => department.is_active),
    [departments.data]
  );

  const departmentName = (id?: string | null) =>
    departments.data?.find((department) => department.id === id)?.name ?? 'Unassigned';

  if (!isAdmin) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/hospital">
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back
          </Link>
        </Button>
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            You need an administrator account to manage departments and doctors.
          </CardContent>
        </Card>
      </div>
    );
  }

  const submitDepartment = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!departmentForm.name.trim()) {
      toast.error('Department name is required');
      return;
    }
    try {
      if (editingDepartment) {
        await updateDepartment.mutateAsync({
          id: editingDepartment.id,
          input: clean(departmentForm),
        });
        toast.success('Department updated');
      } else {
        await createDepartment.mutateAsync(clean(departmentForm));
        toast.success('Department created');
      }
      setDepartmentForm(emptyDepartment);
      setEditingDepartment(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not save department');
    }
  };

  const editDepartment = (department: HospitalDepartment) => {
    setEditingDepartment(department);
    setDepartmentForm({
      name: department.name,
      code: department.code ?? '',
      head_of_department: department.head_of_department ?? '',
      location: department.location ?? '',
      phone_extension: department.phone_extension ?? '',
    });
  };

  const removeDepartment = async (department: HospitalDepartment) => {
    try {
      await deactivateDepartment.mutateAsync(department.id);
      toast.success(`${department.name} deactivated`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not deactivate department');
    }
  };

  const submitStaff = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!staffForm.first_name.trim() || !staffForm.last_name.trim()) {
      toast.error('First and last name are required');
      return;
    }
    try {
      const payload = clean(staffForm) as StaffInput;
      if (editingStaff && !staffForm.user_id) payload.user_id = null;
      if (editingStaff && !staffForm.department_id) {
        payload.department_id = null;
      }
      if (editingStaff) {
        await updateStaff.mutateAsync({ id: editingStaff.id, input: payload });
        toast.success('Doctor / staff member updated');
      } else {
        await createStaff.mutateAsync(payload);
        toast.success('Doctor / staff member created');
      }
      setStaffForm(emptyStaff);
      setEditingStaff(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not save staff member');
    }
  };

  const editStaff = (member: HospitalStaff) => {
    setEditingStaff(member);
    setStaffForm({
      user_id: member.user_id ?? undefined,
      first_name: member.first_name,
      last_name: member.last_name,
      role: member.role,
      speciality: member.speciality ?? '',
      department_id: member.department_id ?? '',
      phone: member.phone ?? '',
      email: member.email ?? '',
      license_number: member.license_number ?? '',
      max_hours_per_week: member.max_hours_per_week,
    });
  };

  const removeStaff = async (member: HospitalStaff) => {
    try {
      await deactivateStaff.mutateAsync(member.id);
      toast.success(`${member.first_name} ${member.last_name} deactivated`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not deactivate staff member');
    }
  };

  return (
    <div className="space-y-6">
      <FacilitySelect
        value={facilityId}
        onChange={changeFacility}
        disabled={createStaff.isPending || updateStaff.isPending || deactivateStaff.isPending ||
          createDepartment.isPending || updateDepartment.isPending || deactivateDepartment.isPending}
      />
      {!facilityId && <p className="text-sm text-muted-foreground">Showing your current facility. Select another facility to manage its directory.</p>}
      <div>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/hospital">
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to hospital admin
          </Link>
        </Button>
        <h1 className="mt-2 flex items-center gap-2 text-2xl font-bold">
          <Building2 className="h-6 w-6 text-healthcare-green" />
          Departments &amp; Doctors
        </h1>
        <p className="text-muted-foreground">
          Changes are saved to the database and appear immediately in registration routing.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        {/* ── Departments ─────────────────────────────────────────────── */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Plus className="h-4 w-4" />
                {editingDepartment ? 'Edit department' : 'Add department'}
              </CardTitle>
              <CardDescription>
                Departments are used as patient destinations during registration.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={submitDepartment} className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1 sm:col-span-2">
                    <label className="text-sm font-medium">Name *</label>
                    <Input
                      value={departmentForm.name}
                      onChange={(event) =>
                        setDepartmentForm((prev) => ({ ...prev, name: event.target.value }))
                      }
                      placeholder="e.g. Outpatient Department"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Code</label>
                    <Input
                      value={departmentForm.code}
                      onChange={(event) =>
                        setDepartmentForm((prev) => ({ ...prev, code: event.target.value }))
                      }
                      placeholder="e.g. OPD"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Phone extension</label>
                    <Input
                      value={departmentForm.phone_extension}
                      onChange={(event) =>
                        setDepartmentForm((prev) => ({
                          ...prev,
                          phone_extension: event.target.value,
                        }))
                      }
                      placeholder="e.g. 4210"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Head of department</label>
                    <Input
                      value={departmentForm.head_of_department}
                      onChange={(event) =>
                        setDepartmentForm((prev) => ({
                          ...prev,
                          head_of_department: event.target.value,
                        }))
                      }
                      placeholder="Clinician name"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Location</label>
                    <Input
                      value={departmentForm.location}
                      onChange={(event) =>
                        setDepartmentForm((prev) => ({ ...prev, location: event.target.value }))
                      }
                      placeholder="e.g. Block B, ground floor"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button type="submit" disabled={createDepartment.isPending || updateDepartment.isPending}>
                    {(createDepartment.isPending || updateDepartment.isPending) && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    {editingDepartment ? 'Save changes' : 'Create department'}
                  </Button>
                  {editingDepartment && (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setEditingDepartment(null);
                        setDepartmentForm(emptyDepartment);
                      }}
                    >
                      Cancel
                    </Button>
                  )}
                </div>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Departments ({departments.data?.length ?? 0})</CardTitle>
            </CardHeader>
            <CardContent>
              {departments.isLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : departments.isError ? (
                <p className="text-sm text-destructive">
                  {departments.error instanceof Error
                    ? departments.error.message
                    : 'Could not load departments'}
                </p>
              ) : (departments.data?.length ?? 0) === 0 ? (
                <p className="text-sm text-muted-foreground">No departments yet.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Department</TableHead>
                      <TableHead>Code</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(departments.data ?? []).map((department) => (
                      <TableRow key={department.id}>
                        <TableCell>
                          <p className="font-medium">{department.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {department.location || 'No location'}
                          </p>
                        </TableCell>
                        <TableCell>{department.code || '—'}</TableCell>
                        <TableCell>
                          <Badge variant={department.is_active ? 'success' : 'outline'}>
                            {department.is_active ? 'active' : 'inactive'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button size="sm" variant="ghost" onClick={() => editDepartment(department)}>
                              <Pencil className="h-4 w-4" />
                            </Button>
                            {department.is_active && (
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={deactivateDepartment.isPending}
                                onClick={() => removeDepartment(department)}
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── Staff / doctors ─────────────────────────────────────────── */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Stethoscope className="h-4 w-4" />
                {editingStaff ? 'Edit doctor / staff member' : 'Add doctor / staff member'}
              </CardTitle>
              <CardDescription>
                Doctors and nurses appear in the registration “send to” selectors.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={submitStaff} className="space-y-3">
                <div className="space-y-1">
                  <label htmlFor="staff-login-account" className="text-sm font-medium">Login account</label>
                  <Select value={staffForm.user_id || 'none'} onValueChange={(value) =>
                    setStaffForm((prev) => ({ ...prev, user_id: value === 'none' ? undefined : value }))
                  }>
                    <SelectTrigger id="staff-login-account"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No linked account</SelectItem>
                      {staffForm.user_id && !eligibleAccounts.some((account) => account.id === staffForm.user_id) && (
                        <SelectItem value={staffForm.user_id}>Current linked account</SelectItem>
                      )}
                      {eligibleAccounts.map((account) => (
                        <SelectItem key={account.id} value={account.id}>{account.email || account.id}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">Link a login assigned to this facility so this staff member can receive patient handoffs.</p>
                  {staffAccounts.isError && <p role="alert" className="text-sm text-destructive">Could not load login accounts.</p>}
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <label className="text-sm font-medium">First name *</label>
                    <Input
                      value={staffForm.first_name}
                      onChange={(event) =>
                        setStaffForm((prev) => ({ ...prev, first_name: event.target.value }))
                      }
                      placeholder="First name"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Last name *</label>
                    <Input
                      value={staffForm.last_name}
                      onChange={(event) =>
                        setStaffForm((prev) => ({ ...prev, last_name: event.target.value }))
                      }
                      placeholder="Last name"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Role</label>
                    <Select
                      value={staffForm.role}
                      onValueChange={(value) =>
                        setStaffForm((prev) => ({ ...prev, role: value as HospitalStaffRole }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {staffRoles.map((role) => (
                          <SelectItem key={role.value} value={role.value}>
                            {role.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Department</label>
                    <Select
                      value={staffForm.department_id || 'none'}
                      onValueChange={(value) =>
                        setStaffForm((prev) => ({
                          ...prev,
                          department_id: value === 'none' ? '' : value,
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Unassigned" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Unassigned</SelectItem>
                        {activeDepartments.map((department) => (
                          <SelectItem key={department.id} value={department.id}>
                            {department.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Speciality</label>
                    <Input
                      value={staffForm.speciality}
                      onChange={(event) =>
                        setStaffForm((prev) => ({ ...prev, speciality: event.target.value }))
                      }
                      placeholder="e.g. Internal medicine"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">License number</label>
                    <Input
                      value={staffForm.license_number}
                      onChange={(event) =>
                        setStaffForm((prev) => ({ ...prev, license_number: event.target.value }))
                      }
                      placeholder="e.g. HPCZ-12345"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Phone</label>
                    <Input
                      value={staffForm.phone}
                      onChange={(event) =>
                        setStaffForm((prev) => ({ ...prev, phone: event.target.value }))
                      }
                      placeholder="+260 ..."
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Email</label>
                    <Input
                      type="email"
                      value={staffForm.email}
                      onChange={(event) =>
                        setStaffForm((prev) => ({ ...prev, email: event.target.value }))
                      }
                      placeholder="clinician@hospital.zm"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button type="submit" disabled={createStaff.isPending || updateStaff.isPending}>
                    {(createStaff.isPending || updateStaff.isPending) && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    {editingStaff ? 'Save changes' : 'Create staff member'}
                  </Button>
                  {editingStaff && (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setEditingStaff(null);
                        setStaffForm(emptyStaff);
                      }}
                    >
                      Cancel
                    </Button>
                  )}
                </div>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Doctors &amp; staff ({staff.data?.total ?? 0})</CardTitle>
            </CardHeader>
            <CardContent>
              {staff.isLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : staff.isError ? (
                <p className="text-sm text-destructive">
                  {staff.error instanceof Error ? staff.error.message : 'Could not load staff'}
                </p>
              ) : (staff.data?.items.length ?? 0) === 0 ? (
                <p className="text-sm text-muted-foreground">No staff members yet.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Department</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(staff.data?.items ?? []).map((member) => (
                      <TableRow key={member.id}>
                        <TableCell>
                          <p className="flex items-center gap-1 font-medium">
                            <UserRound className="h-3.5 w-3.5" />
                            {member.first_name} {member.last_name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {member.speciality || member.email || 'No speciality'}
                          </p>
                        </TableCell>
                        <TableCell className="capitalize">
                          {member.role.replace(/_/g, ' ')}
                        </TableCell>
                        <TableCell>{departmentName(member.department_id)}</TableCell>
                        <TableCell>
                          <Badge variant={member.is_active ? 'success' : 'outline'}>
                            {member.is_active ? 'active' : 'inactive'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button size="sm" variant="ghost" onClick={() => editStaff(member)}>
                              <Pencil className="h-4 w-4" />
                            </Button>
                            {member.is_active && (
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={deactivateStaff.isPending}
                                onClick={() => removeStaff(member)}
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
