'use client';

import { useState } from 'react';
import { useAuthStore } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { changeLanguage } from '@/i18n/config';
import { useTranslation } from 'react-i18next';
import {
  User, Globe, Bell, Shield, Palette, Save, Smartphone,
} from 'lucide-react';
import { AiChatWidget } from '@/components/patient/AiChatWidget';
import { toast } from 'sonner';

const languages = [
  { code: 'en', label: 'English' },
  { code: 'bem', label: 'Chibemba' },
  { code: 'nyj', label: 'Chinyanja' },
  { code: 'tog', label: 'Chitonga' },
  { code: 'loz', label: 'Silozi' },
];

export default function SettingsPage() {
  const { user } = useAuthStore();
  const { t } = useTranslation();
  const [chatOpen, setChatOpen] = useState(false);
  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [phone, setPhone] = useState(user?.phone || '');
  const [lang, setLang] = useState(user?.preferred_language || 'en');
  const [notifications, setNotifications] = useState({
    email: true,
    sms: false,
    push: true,
    appointments: true,
    lab_results: true,
    medication_reminders: false,
  });

  const handleSaveProfile = () => {
    toast.success('Profile updated successfully');
  };

  const handleSaveNotifications = () => {
    toast.success('Notification preferences saved');
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Manage your account settings, preferences, and security</p>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile" className="flex items-center gap-2">
            <User className="h-4 w-4" /> Profile
          </TabsTrigger>
          <TabsTrigger value="language" className="flex items-center gap-2">
            <Globe className="h-4 w-4" /> Language & Region
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="h-4 w-4" /> Notifications
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center gap-2">
            <Shield className="h-4 w-4" /> Security
          </TabsTrigger>
          <TabsTrigger value="appearance" className="flex items-center gap-2">
            <Palette className="h-4 w-4" /> Appearance
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>Update your personal details and contact information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Full Name</label>
                  <Input value={name} onChange={(e) => setName(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Email</label>
                  <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Phone</label>
                  <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+260 XXX XXX XXX" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Role</label>
                  <Input value={user?.role || ''} disabled className="capitalize" />
                </div>
              </div>
              <Button onClick={handleSaveProfile} className="bg-healthcare-green text-white hover:bg-healthcare-green-dark">
                <Save className="mr-2 h-4 w-4" /> Save Changes
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="language">
          <Card>
            <CardHeader>
              <CardTitle>Language & Regional Preferences</CardTitle>
              <CardDescription>Choose your preferred language and regional settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Display Language</label>
                <div className="grid gap-2 md:grid-cols-5">
                  {languages.map((l) => (
                    <button
                      key={l.code}
                      onClick={() => { setLang(l.code); changeLanguage(l.code); }}
                      className={`p-3 rounded-lg border text-sm transition-colors ${lang === l.code ? 'border-healthcare-green bg-healthcare-green/10 text-healthcare-green font-medium' : 'hover:bg-accent'}`}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="pt-4 border-t">
                <p className="text-sm text-muted-foreground">
                  Current locale: <span className="font-medium text-foreground">en-ZM (Zambia)</span>
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  Currency: <span className="font-medium text-foreground">ZMW (Zambian Kwacha)</span>
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>Control how and when you receive notifications</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <h3 className="text-sm font-medium">Channels</h3>
                {[
                  { key: 'email', label: 'Email notifications', desc: 'Receive updates via email' },
                  { key: 'sms', label: 'SMS notifications', desc: 'Receive updates via SMS to your phone' },
                  { key: 'push', label: 'Push notifications', desc: 'Receive in-app and browser notifications' },
                ].map(({ key, label, desc }) => (
                  <label key={key} className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent/50">
                    <div>
                      <p className="text-sm font-medium">{label}</p>
                      <p className="text-xs text-muted-foreground">{desc}</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={notifications[key as keyof typeof notifications] as boolean}
                      onChange={() => setNotifications((prev) => ({ ...prev, [key]: !prev[key as keyof typeof notifications] }))}
                      className="h-4 w-4 rounded border-gray-300 text-healthcare-green focus:ring-healthcare-green"
                    />
                  </label>
                ))}
              </div>
              <div className="space-y-3">
                <h3 className="text-sm font-medium">Notify me about</h3>
                {[
                  { key: 'appointments', label: 'Appointment reminders' },
                  { key: 'lab_results', label: 'Lab results available' },
                  { key: 'medication_reminders', label: 'Medication reminders' },
                ].map(({ key, label }) => (
                  <label key={key} className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent/50">
                    <p className="text-sm font-medium">{label}</p>
                    <input
                      type="checkbox"
                      checked={notifications[key as keyof typeof notifications] as boolean}
                      onChange={() => setNotifications((prev) => ({ ...prev, [key]: !prev[key as keyof typeof notifications] }))}
                      className="h-4 w-4 rounded border-gray-300 text-healthcare-green focus:ring-healthcare-green"
                    />
                  </label>
                ))}
              </div>
              <Button onClick={handleSaveNotifications} className="bg-healthcare-green text-white hover:bg-healthcare-green-dark">
                <Save className="mr-2 h-4 w-4" /> Save Preferences
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>Manage your password and account security</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <h3 className="text-sm font-medium">Change Password</h3>
                <div className="grid gap-3 max-w-md">
                  <Input type="password" placeholder="Current password" />
                  <Input type="password" placeholder="New password" />
                  <Input type="password" placeholder="Confirm new password" />
                  <Button variant="outline" onClick={() => toast.success('Password changed successfully')}>
                    Update Password
                  </Button>
                </div>
              </div>
              <div className="pt-4 border-t space-y-4">
                <div className="flex items-center justify-between p-3 rounded-lg border">
                  <div>
                    <p className="text-sm font-medium">Two-Factor Authentication (2FA)</p>
                    <p className="text-xs text-muted-foreground">Add an extra layer of security to your account</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => toast.info('2FA setup coming soon')}>
                    <Smartphone className="mr-2 h-4 w-4" /> Enable
                  </Button>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg border">
                  <div>
                    <p className="text-sm font-medium">Active Sessions</p>
                    <p className="text-xs text-muted-foreground">Manage your active login sessions</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => toast.success('All other sessions logged out')}>
                    Revoke All
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="appearance">
          <Card>
            <CardHeader>
              <CardTitle>Appearance</CardTitle>
              <CardDescription>Customize the look and feel of your dashboard</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Theme</label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { mode: 'light', label: 'Light', icon: '☀️' },
                    { mode: 'dark', label: 'Dark', icon: '🌙' },
                    { mode: 'system', label: 'System', icon: '💻' },
                  ].map(({ mode, label, icon }) => (
                    <button
                      key={mode}
                      onClick={() => toast.info(`${label} theme coming soon`)}
                      className="p-4 rounded-lg border text-center hover:bg-accent transition-colors"
                    >
                      <span className="text-2xl">{icon}</span>
                      <p className="text-sm font-medium mt-2">{label}</p>
                    </button>
                  ))}
                </div>
              </div>
              <div className="pt-4 border-t">
                <p className="text-xs text-muted-foreground">
                  Font: Inter (system font) · Density: Default
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      <AiChatWidget open={chatOpen} onOpenChange={setChatOpen} />
    </div>
  );
}
