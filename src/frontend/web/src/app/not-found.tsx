import Link from 'next/link';
import { ArrowLeft, Heart, SearchX } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-lg space-y-6 text-center">
        <Link href="/" className="mx-auto inline-flex items-center gap-2 font-semibold text-healthcare-green">
          <Heart className="h-6 w-6" fill="currentColor" />
          UbuntuCare
        </Link>

        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <SearchX className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
        </div>

        <div className="space-y-2">
          <p className="text-sm font-semibold uppercase tracking-widest text-healthcare-green">404</p>
          <h1 className="text-3xl font-bold tracking-tight">Page not found</h1>
          <p className="text-muted-foreground">
            This page may have moved, or the address may be incorrect. Your work has not been changed.
          </p>
        </div>

        <div className="flex flex-col justify-center gap-3 sm:flex-row">
          <Button asChild>
            <Link href="/">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Go to home
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
