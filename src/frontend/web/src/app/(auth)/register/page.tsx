'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Heart, Loader2, Check } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/lib/api-client';

const registerSchema = z.object({
  name: z.string().min(2, 'Name is required'),
  email: z.string().email('Please enter a valid email'),
  phone: z.string().min(10, 'Please enter a valid phone number'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
  acceptTerms: z.boolean().refine((val) => val === true, { message: 'You must accept the terms' }),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState(1);

  const { register, handleSubmit, formState: { errors }, watch } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: { acceptTerms: false },
  });

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true);
    try {
      await api.post('/auth/register', {
        name: data.name,
        email: data.email,
        phone: data.phone,
        password: data.password,
        role: 'patient',
      });
      toast.success('Account created successfully! Please check your email to verify.');
      router.push('/login');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Registration failed. Please try again.');
    }
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-white to-green-100 p-4 py-12">
      <Card className="w-full max-w-lg shadow-xl">
        <CardHeader className="text-center space-y-2">
          <div className="flex justify-center mb-2">
            <div className="w-12 h-12 rounded-full bg-healthcare-green flex items-center justify-center">
              <Heart className="h-7 w-7 text-white" fill="white" />
            </div>
          </div>
          <CardTitle className="text-2xl">Create Patient Account</CardTitle>
          <CardDescription>Join UbuntuCare as a patient</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center gap-2 mb-6">
            {[1, 2].map((s) => (
              <div key={s} className="flex items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${step >= s ? 'bg-healthcare-green text-white' : 'bg-muted text-muted-foreground'}`}>
                  {step > s ? <Check className="h-4 w-4" /> : s}
                </div>
                {s < 2 && <div className={`w-12 h-1 ${step > s ? 'bg-healthcare-green' : 'bg-muted'}`} />}
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {step === 1 && (
              <>
                <div>
                  <label className="text-sm font-medium mb-1 block">Full Name</label>
                  <Input {...register('name')} placeholder="John Banda" />
                  {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name.message}</p>}
                </div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Email</label>
                  <Input {...register('email')} type="email" placeholder="john@example.com" />
                  {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email.message}</p>}
                </div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Phone Number</label>
                  <Input {...register('phone')} placeholder="+260 97 123 4567" />
                  {errors.phone && <p className="text-xs text-red-500 mt-1">{errors.phone.message}</p>}
                </div>
                <Button type="button" className="w-full" onClick={() => setStep(2)}>Next Step</Button>
              </>
            )}

            {step === 2 && (
              <>
                <div>
                  <label className="text-sm font-medium mb-1 block">Password</label>
                  <Input {...register('password')} type="password" placeholder="Min. 8 characters" />
                  {errors.password && <p className="text-xs text-red-500 mt-1">{errors.password.message}</p>}
                </div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Confirm Password</label>
                  <Input {...register('confirmPassword')} type="password" placeholder="Repeat your password" />
                  {errors.confirmPassword && <p className="text-xs text-red-500 mt-1">{errors.confirmPassword.message}</p>}
                </div>
                <div className="p-4 rounded-lg bg-muted/50 space-y-2">
                  <p className="font-medium">Account Summary</p>
                  <p className="text-sm text-muted-foreground">Name: {watch('name')}</p>
                  <p className="text-sm text-muted-foreground">Email: {watch('email')}</p>
                  <p className="text-sm text-muted-foreground">Role: Patient</p>
                </div>
                <label className="flex items-start gap-2 text-sm">
                  <input type="checkbox" {...register('acceptTerms')} className="mt-0.5 rounded border-gray-300" />
                  <span>I accept the Terms of Service and Privacy Policy</span>
                </label>
                {errors.acceptTerms && <p className="text-xs text-red-500">{errors.acceptTerms.message}</p>}
                <div className="flex gap-2">
                  <Button type="button" variant="outline" className="w-full" onClick={() => setStep(1)}>Back</Button>
                  <Button type="submit" className="w-full bg-healthcare-green hover:bg-healthcare-green-dark" disabled={isLoading}>
                    {isLoading ? <Loader2 className="h-5 w-5 animate-spin mr-2" /> : null}
                    Create Account
                  </Button>
                </div>
              </>
            )}
          </form>
        </CardContent>
        <CardFooter className="justify-center">
          <p className="text-sm text-muted-foreground">
            Already have an account? <Link href="/login" className="text-healthcare-green hover:underline font-medium">Sign in</Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
