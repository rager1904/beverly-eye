'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Bell, ArrowLeft, Save } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

export default function NotificationSettingsPage() {
  const [notifications, setNotifications] = useState({
    email: true, sms: false, push: true,
    appointments: true, lab_results: true, medication_reminders: false,
  });

  const toggle = (key: string) => setNotifications((prev) => ({ ...prev, [key]: !prev[key as keyof typeof prev] }));

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" asChild><Link href="/settings"><ArrowLeft className="h-4 w-4 mr-1" />Back to Settings</Link></Button>
      </div>
      <h1 className="text-2xl font-bold flex items-center gap-2"><Bell className="h-6 w-6 text-amber-600" />Notification Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Channels</CardTitle>
          <CardDescription>Choose how you receive notifications</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            { key: 'email', label: 'Email', desc: 'Receive updates via email' },
            { key: 'sms', label: 'SMS', desc: 'Receive updates via SMS to your phone' },
            { key: 'push', label: 'Push', desc: 'Receive in-app and browser notifications' },
          ].map(({ key, label, desc }) => (
            <label key={key} className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent/50 cursor-pointer">
              <div><p className="text-sm font-medium">{label}</p><p className="text-xs text-muted-foreground">{desc}</p></div>
              <input type="checkbox" checked={notifications[key as keyof typeof notifications] as boolean} onChange={() => toggle(key)} className="h-4 w-4" />
            </label>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Notification Types</CardTitle>
          <CardDescription>Choose what to be notified about</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            { key: 'appointments', label: 'Appointment reminders' },
            { key: 'lab_results', label: 'Lab results available' },
            { key: 'medication_reminders', label: 'Medication reminders' },
          ].map(({ key, label }) => (
            <label key={key} className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent/50 cursor-pointer">
              <p className="text-sm font-medium">{label}</p>
              <input type="checkbox" checked={notifications[key as keyof typeof notifications] as boolean} onChange={() => toggle(key)} className="h-4 w-4" />
            </label>
          ))}
        </CardContent>
      </Card>

      <Button onClick={() => { toast.success('Preferences saved'); }}>
        <Save className="h-4 w-4 mr-2" />Save Preferences
      </Button>
    </div>
  );
}
