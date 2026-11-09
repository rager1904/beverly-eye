'use client';

import { useState, useEffect, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { UserPlus, Shield, AlertCircle, CheckCircle2, Search, Building2 } from 'lucide-react';
import { api } from '@/lib/api-client';

const createUserSchema = z.object({
  name: z.string().min(2, 'Name is required'),
  email: z.string().email('Valid email is required'),
  phone: z.string().min(10, 'Valid phone number is required'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  role: z.string().min(1, 'Role is required'),
});

type CreateUserForm = z.infer<typeof createUserSchema>;

const roles = [
  { value: 'admin', label: 'Admin' },
  { value: 'provider', label: 'Provider (Doctor)' },
  { value: 'nurse', label: 'Nurse' },
  { value: 'patient', label: 'Patient' },
  { value: 'lab_tech', label: 'Lab Technician' },
  { value: 'pharmacist', label: 'Pharmacist' },
  { value: 'public_health', label: 'Public Health Officer' },
  { value: 'community_health_worker', label: 'Community Health Worker' },
  { value: 'ministry_official', label: 'Ministry Official' },
];

interface KeycloakUser {
  id: string;
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  enabled: boolean;
  hospital_id: string | null;
  emailVerified: boolean;
}

interface Hospital {
  id: string;
  name: string;
  code: string;
  province: string;
  district: string;
}

export default function ManageUsersPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);
  const [users, setUsers] = useState<KeycloakUser[]>([]);
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [searching, setSearching] = useState(false);
  const [assigning, setAssigning] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors }, reset, setValue, watch } = useForm<CreateUserForm>({
    resolver: zodResolver(createUserSchema),
  });

  const selectedRole = watch('role');

  useEffect(() => {
    (async () => {
      try { const data: Hospital[] = await api.get('/hospital/list'); setHospitals(data); } catch {}
    })();
  }, []);

  const searchUsers = useCallback(async () => {
    setSearching(true);
    try {
      const data: KeycloakUser[] = await api.get(`/auth/admin/users?search=${encodeURIComponent(searchTerm)}`);
      setUsers(data);
    } catch {
      setResult({ success: false, message: 'Failed to search users' });
    }
    setSearching(false);
  }, [searchTerm]);

  const assignHospital = async (userId: string, hospitalId: string) => {
    setAssigning(userId);
    try {
      await api.put(`/auth/admin/users/${userId}/hospital`, { hospital_id: hospitalId });
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, hospital_id: hospitalId } : u)));
    } catch {
      setResult({ success: false, message: 'Failed to assign hospital' });
    }
    setAssigning(null);
  };

  const onSubmit = async (data: CreateUserForm) => {
    setIsLoading(true);
    setResult(null);
    try {
      await api.post('/auth/admin/register', {
        name: data.name,
        email: data.email,
        phone: data.phone,
        password: data.password,
        role: data.role,
      });
      setResult({ success: true, message: 'User created successfully.' });
      reset();
    } catch (error) {
      setResult({
        success: false,
        message: error instanceof Error ? error.message : 'Failed to create user',
      });
    }
    setIsLoading(false);
  };

  const fullName = (u: KeycloakUser) => [u.firstName, u.lastName].filter(Boolean).join(' ') || u.username;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">User Management</h1>
          <p className="text-muted-foreground">Create, search, and manage user accounts</p>
        </div>
      </div>

      {result && (
        <div className={`p-4 rounded-lg border flex items-start gap-3 ${result.success ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
          {result.success ? <CheckCircle2 className="h-5 w-5 mt-0.5 shrink-0" /> : <AlertCircle className="h-5 w-5 mt-0.5 shrink-0" />}
          <div>
            <p className="font-medium">{result.success ? 'Success' : 'Error'}</p>
            <p className="text-sm mt-1">{result.message}</p>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <UserPlus className="h-4 w-4" /> Create New User
            </CardTitle>
            <CardDescription>Manually create a user with any role</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-sm font-medium">Full Name</label>
                  <Input {...register('name')} placeholder="John Banda" />
                  {errors.name && <p className="text-xs text-red-500">{errors.name.message}</p>}
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Email</label>
                  <Input type="email" {...register('email')} placeholder="john@example.com" />
                  {errors.email && <p className="text-xs text-red-500">{errors.email.message}</p>}
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Phone</label>
                  <Input {...register('phone')} placeholder="+260 97 123 4567" />
                  {errors.phone && <p className="text-xs text-red-500">{errors.phone.message}</p>}
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Role</label>
                  <Select onValueChange={(v) => setValue('role', v)} value={selectedRole}>
                    <SelectTrigger><SelectValue placeholder="Select role" /></SelectTrigger>
                    <SelectContent>
                      {roles.map((r) => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <input type="hidden" {...register('role')} />
                  {errors.role && <p className="text-xs text-red-500">{errors.role.message}</p>}
                </div>
                <div className="space-y-1 col-span-2">
                  <label className="text-sm font-medium">Temporary Password</label>
                  <Input type="password" {...register('password')} placeholder="Min. 8 characters" />
                  {errors.password && <p className="text-xs text-red-500">{errors.password.message}</p>}
                </div>
              </div>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Creating...' : 'Create User'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Search className="h-4 w-4" /> Search Users
            </CardTitle>
            <CardDescription>Find users by name or email</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} placeholder="Search..." onKeyDown={(e) => e.key === 'Enter' && searchUsers()} />
              <Button onClick={searchUsers} disabled={searching}>{searching ? '...' : 'Search'}</Button>
            </div>

            {users.length > 0 && (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {users.map((user) => (
                  <div key={user.id} className="p-3 rounded-lg border text-sm space-y-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{fullName(user)}</p>
                        <p className="text-xs text-muted-foreground">{user.email}</p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${user.enabled ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {user.enabled ? 'Active' : 'Disabled'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-muted-foreground shrink-0" />
                      <Select
                        value={user.hospital_id || ''}
                        onValueChange={(v) => assignHospital(user.id, v)}
                        disabled={assigning === user.id}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue placeholder="No hospital assigned" />
                        </SelectTrigger>
                        <SelectContent>
                          {hospitals.map((h) => (
                            <SelectItem key={h.id} value={h.id}>{h.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
