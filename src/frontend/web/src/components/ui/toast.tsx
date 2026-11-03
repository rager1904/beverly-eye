import { Toaster as SonnerToaster } from 'sonner';

export function Toaster() {
  return (
    <SonnerToaster
      position="top-right"
      toastOptions={{
        duration: 5000,
        className: 'border border-border shadow-lg',
        style: { background: 'hsl(var(--background))', color: 'hsl(var(--foreground))' },
      }}
      richColors
      closeButton
    />
  );
}

export { toast } from 'sonner';
