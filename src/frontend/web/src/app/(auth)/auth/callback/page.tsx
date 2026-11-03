'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/lib/auth';

function CallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { handleKeycloakCallback } = useAuthStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    if (!code) {
      setError('No authorization code received from Keycloak');
      return;
    }
    handleKeycloakCallback(code)
      .then(() => {
        const role = useAuthStore.getState().user?.role;
        if (role === 'patient') router.push('/patient');
        else if (role === 'admin') router.push('/hospital');
        else if (role === 'public_health') router.push('/public-health');
        else if (role === 'pharmacist') router.push('/pharmacy');
        else if (role === 'lab_tech') router.push('/laboratory');
        else router.push('/provider');
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Authentication failed');
      });
  }, [searchParams, handleKeycloakCallback, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4 max-w-md p-8">
          <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto">
            <span className="text-2xl">!</span>
          </div>
          <h1 className="text-xl font-bold">Authentication Failed</h1>
          <p className="text-muted-foreground">{error}</p>
          <a href="/login" className="text-sm text-healthcare-green hover:underline">Return to login</a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-4">
        <div className="w-16 h-16 rounded-full bg-healthcare-green/10 flex items-center justify-center mx-auto animate-pulse">
          <div className="w-4 h-4 rounded-full bg-healthcare-green" />
        </div>
        <h1 className="text-lg font-medium">Completing authentication...</h1>
        <p className="text-sm text-muted-foreground">Redirecting to your dashboard</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    }>
      <CallbackInner />
    </Suspense>
  );
}
