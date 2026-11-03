import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date, options?: Intl.DateTimeFormatOptions): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-ZM', options || { year: 'numeric', month: 'short', day: 'numeric' });
}

export function formatTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleTimeString('en-ZM', { hour: '2-digit', minute: '2-digit' });
}

export function formatDateTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return `${formatDate(d)} ${formatTime(d)}`;
}

export function formatZMW(amount: number): string {
  return new Intl.NumberFormat('en-ZM', {
    style: 'currency',
    currency: 'ZMW',
    minimumFractionDigits: 2,
  }).format(amount);
}

export function formatPercentage(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export function calculateAge(dateOfBirth: string): number {
  const birth = new Date(dateOfBirth);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) age--;
  return age;
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    active: 'text-green-600 bg-green-50',
    completed: 'text-blue-600 bg-blue-50',
    scheduled: 'text-purple-600 bg-purple-50',
    cancelled: 'text-red-600 bg-red-50',
    pending: 'text-amber-600 bg-amber-50',
    'in-progress': 'text-teal-600 bg-teal-50',
    waiting: 'text-yellow-600 bg-yellow-50',
    critical: 'text-red-700 bg-red-100',
    normal: 'text-green-700 bg-green-100',
    urgent: 'text-orange-700 bg-orange-100',
  };
  return colors[status] || 'text-gray-600 bg-gray-50';
}

export function getPriorityColor(priority: string): string {
  const colors: Record<string, string> = {
    emergency: 'bg-red-100 text-red-800 border-red-200',
    urgent: 'bg-orange-100 text-orange-800 border-orange-200',
    normal: 'bg-green-100 text-green-800 border-green-200',
  };
  return colors[priority] || 'bg-gray-100 text-gray-800 border-gray-200';
}

export function classNames(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function debounce<T extends (...args: unknown[]) => unknown>(fn: T, ms: number): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

export function generateId(): string {
  return crypto.randomUUID?.() || Math.random().toString(36).substring(2, 15);
}
