'use client';

import { useState, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import {
  LayoutDashboard, Users, Calendar, Video, FileText, BarChart3, Activity, Pill, FlaskConical,
  Settings, LogOut, Menu, X, Bell, Heart, ChevronLeft, ChevronRight, Search, Globe, BookOpen, Bot, UserCog, Building2
} from 'lucide-react';
import { getInitials } from '@/lib/utils';
import { changeLanguage } from '@/i18n/config';
import { useTranslation } from 'react-i18next';

const sidebarItems = [
  { href: '/provider', label: 'Provider Dashboard', icon: LayoutDashboard, roles: ['provider', 'nurse'] },
  { href: '/patient', label: 'Patient Dashboard', icon: LayoutDashboard, roles: ['patient'] },
  { href: '/patient/education', label: 'Health Education', icon: BookOpen, roles: ['patient'] },
  { href: '/hospital', label: 'Hospital Admin', icon: LayoutDashboard, roles: ['admin'] },
  { href: '/telemedicine', label: 'Telemedicine', icon: Video, roles: ['provider', 'patient', 'nurse'] },
  { href: '/emr', label: 'EMR', icon: FileText, roles: ['provider', 'nurse'] },
  { href: '/patient-flow', label: 'Patient Flow', icon: Activity, roles: ['provider', 'nurse', 'admin', 'records_officer', 'medical_records', 'clinical_officer', 'receptionist', 'lab_tech', 'pharmacist'] },
  { href: '/clinical-notes', label: 'Clinical Notes', icon: FileText, roles: ['provider', 'nurse', 'admin'] },
  { href: '/analytics', label: 'Analytics', icon: BarChart3, roles: ['provider', 'admin'] },
  { href: '/public-health', label: 'Public Health', icon: Activity, roles: ['provider', 'admin', 'public_health'] },
  { href: '/pharmacy', label: 'Pharmacy', icon: Pill, roles: ['pharmacist', 'admin'] },
  { href: '/laboratory', label: 'Laboratory', icon: FlaskConical, roles: ['lab_tech', 'provider', 'nurse', 'admin'] },
  { href: '/hospital/admit', label: 'Admit Patient', icon: Building2, roles: ['provider', 'nurse', 'admin'] },
  { href: '/ai-guide', label: 'AI Assistant Guide', icon: Bot, roles: ['patient', 'provider', 'nurse', 'admin', 'lab_tech', 'pharmacist', 'public_health'] },
  { href: '/settings/users', label: 'User Management', icon: UserCog, roles: ['admin'] },
  { href: '/settings/directory', label: 'Departments & Doctors', icon: Users, roles: ['admin'] },
  { href: '/settings/hospitals', label: 'Facilities', icon: Building2, roles: ['admin'] },
];

const languages = [
  { code: 'en', label: 'English' },
  { code: 'bem', label: 'Chibemba' },
  { code: 'nyj', label: 'Chinyanja' },
  { code: 'tog', label: 'Chitonga' },
  { code: 'loz', label: 'Silozi' },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, accessToken, isAuthenticated, isLoading, logout, fetchUserProfile } = useAuthStore();
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useTranslation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);

  useEffect(() => {
    if (isAuthenticated && accessToken && !user && !isLoading) {
      fetchUserProfile().catch(() => router.push('/login'));
      return;
    }
    if (!isAuthenticated && !isLoading) router.push('/login');
  }, [accessToken, fetchUserProfile, isAuthenticated, isLoading, router, user]);

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-sm text-muted-foreground">Loading your dashboard...</div>
      </div>
    );
  }

  const filteredLinks = sidebarItems.filter((item) => item.roles.includes(user.role));

  return (
    <div className="min-h-screen bg-background">
      <aside className={`fixed inset-y-0 left-0 z-50 bg-card border-r transition-all duration-300 ${sidebarOpen ? 'w-64' : 'w-16'} ${mobileOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>
        <div className="flex items-center justify-between h-16 px-4 border-b">
          {sidebarOpen ? (
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-healthcare-green flex items-center justify-center flex-shrink-0">
                <Heart className="h-5 w-5 text-white" fill="white" />
              </div>
              <span className="font-bold text-sm truncate">{t('app.name')}</span>
            </Link>
          ) : (
            <div className="w-8 h-8 rounded-full bg-healthcare-green flex items-center justify-center mx-auto">
              <Heart className="h-5 w-5 text-white" fill="white" />
            </div>
          )}
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="hidden lg:block p-1 rounded-md hover:bg-accent">
            {sidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
        </div>

        <nav className="p-2 space-y-1">
          {filteredLinks.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href || pathname.startsWith(href + '/');
            return (
              <Link key={href} href={href} onClick={() => setMobileOpen(false)}>
                <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${isActive ? 'bg-healthcare-green/10 text-healthcare-green font-medium' : 'text-muted-foreground hover:bg-accent hover:text-foreground'}`}>
                  <Icon className={`h-5 w-5 flex-shrink-0 ${isActive ? 'text-healthcare-green' : ''}`} />
                  {sidebarOpen && <span className="truncate">{label}</span>}
                </div>
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-2 border-t">
          <Link href="/settings">
            <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors`}>
              <Settings className="h-5 w-5 flex-shrink-0" />
              {sidebarOpen && <span>Settings</span>}
            </div>
          </Link>
        </div>
      </aside>

      {mobileOpen && <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setMobileOpen(false)} />}

      <div className={`transition-all duration-300 ${sidebarOpen ? 'lg:pl-64' : 'lg:pl-16'}`}>
        <header className="sticky top-0 z-30 bg-background/80 backdrop-blur-md border-b">
          <div className="flex items-center justify-between h-16 px-4 md:px-6">
            <div className="flex items-center gap-3">
              <button onClick={() => setMobileOpen(true)} className="lg:hidden p-2 rounded-md hover:bg-accent">
                <Menu className="h-5 w-5" />
              </button>
              <div className="relative hidden sm:block">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input type="search" placeholder={t('patient.searchPatients')} className="h-9 w-64 rounded-md border border-input bg-background pl-9 pr-3 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="relative">
                <Button variant="ghost" size="icon" onClick={() => setLangOpen(!langOpen)} className="relative">
                  <Globe className="h-5 w-5" />
                </Button>
                {langOpen && (
                  <div className="absolute right-0 top-full mt-1 w-40 bg-card border rounded-lg shadow-lg p-1 z-50">
                    {languages.map((lang) => (
                      <button key={lang.code} onClick={() => { changeLanguage(lang.code); setLangOpen(false); }}
                        className="w-full text-left px-3 py-2 text-sm rounded-md hover:bg-accent transition-colors">
                        {lang.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-[10px] font-bold text-white flex items-center justify-center">3</span>
              </Button>

              <div className="flex items-center gap-2">
                <Avatar className="h-8 w-8 cursor-pointer">
                  {user.avatar_url ? <AvatarImage src={user.avatar_url} /> : null}
                  <AvatarFallback className="bg-healthcare-green/10 text-healthcare-green text-xs">{getInitials(user.name)}</AvatarFallback>
                </Avatar>
                <div className="hidden md:block">
                  <p className="text-sm font-medium leading-tight">{user.name}</p>
                  <p className="text-xs text-muted-foreground capitalize">{user.role}</p>
                </div>
              </div>

              <Button variant="ghost" size="icon" onClick={logout} className="text-muted-foreground hover:text-red-500">
                <LogOut className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </header>

        <main className="p-4 md:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
