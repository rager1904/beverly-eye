'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Activity, ArrowRight, BarChart3, BookOpen, Building2,
  CheckCircle2, ClipboardPenLine, Database, FileText, Globe2,
  GraduationCap, Heart, Landmark, LockKeyhole, Mail, MapPin,
  Menu, MessageSquareText, Network, Phone, ShieldCheck,
  Users, Video, X, HeartPulse,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const navItems = [
  { label: 'Features', href: '#features' },
  { label: 'Guidelines', href: '/guidelines' },
  { label: 'Privacy', href: '/privacy' },
  { label: 'Terms', href: '/terms' },
  { label: 'Contact', href: '#contact' },
];

const features = [
  { icon: ClipboardPenLine, title: 'Provider AI Assistant', text: 'Ambient clinical documentation, SOAP note support, and structured encounter summaries that reduce charting burden.' },
  { icon: MessageSquareText, title: 'Patient Voice Assistant', text: 'Guided intake, education, and follow-up workflows designed for multilingual patient engagement.' },
  { icon: Database, title: 'Secure Electronic Health Records', text: 'Longitudinal patient records, encounters, vitals, medications, orders, and care history in one clinical workspace.' },
  { icon: Video, title: 'Telemedicine', text: 'Remote consultation tools for extending specialist access to districts, rural clinics, and community programs.' },
  { icon: BarChart3, title: 'Healthcare Analytics', text: 'Operational, clinical, and public-health intelligence for hospitals, programs, and decision makers.' },
  { icon: BookOpen, title: 'Medical Knowledge Search', text: 'AI-assisted research and clinical knowledge retrieval to support safer, faster healthcare decisions.' },
  { icon: Activity, title: 'Public Health Insights', text: 'Disease surveillance, outbreak signals, and population health dashboards built for regional coordination.' },
  { icon: Network, title: 'Appointment Management', text: 'Scheduling, queues, reminders, and patient-flow visibility for busy facilities and distributed teams.' },
];

const trustItems = [
  { icon: LockKeyhole, title: 'End-to-end protection', text: 'Encrypted data flows, secure token-based authentication, and hardened service boundaries.' },
  { icon: Users, title: 'Role-based access', text: 'Clinicians, administrators, lab teams, pharmacists, and public-health users see only what they need.' },
  { icon: FileText, title: 'Audit logging', text: 'Traceable access and operational events to support governance and accountability.' },
  { icon: ShieldCheck, title: 'Secure deployment', text: 'Designed for cloud, hospital, and edge environments with production-grade controls.' },
];

const partners = [
  { icon: Building2, title: 'Hospitals', text: 'Modernize clinical operations, records, telemedicine, bed visibility, and care coordination.' },
  { icon: Landmark, title: 'Government Agencies', text: 'Strengthen national digital health infrastructure, public-health analytics, and data-driven planning.' },
  { icon: GraduationCap, title: 'Universities', text: 'Enable medical research, AI evaluation, student training, and clinical innovation programs.' },
  { icon: Globe2, title: 'NGOs & Research Institutions', text: 'Run evidence-based programs with secure data capture, reporting, and patient engagement.' },
];

const pricingTracks = [
  'Clinic and district facility pilots',
  'Hospital and teaching hospital deployment',
  'Government, NGO, and research partnerships',
];

export default function LandingPage() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white text-slate-950">
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
        <div className="container mx-auto px-4">
          <div className="flex h-16 items-center justify-between">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-healthcare-green">
                <Heart className="h-5 w-5 text-white" fill="white" />
              </div>
              <div className="leading-tight">
                <p className="text-lg font-bold">UbuntuCare</p>
                <p className="text-[11px] font-medium text-slate-500">Ubumi Bwakwe Bwikala Mu Zambia</p>
              </div>
            </Link>

            <nav className="hidden items-center gap-7 md:flex">
              {navItems.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-950"
                >
                  {item.label}
                </a>
              ))}
            </nav>

            <div className="hidden items-center gap-3 md:flex">
              <Button asChild variant="outline" size="sm">
                <Link href="/login">Sign In</Link>
              </Button>
              <Button asChild size="sm" className="bg-healthcare-green text-white hover:bg-healthcare-green-dark">
                <a href="#contact">Request Demo</a>
              </Button>
            </div>

            <button className="md:hidden" onClick={() => setMobileOpen((o) => !o)} aria-label="Toggle menu">
              {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>

          {mobileOpen && (
            <div className="border-t border-slate-200 py-4 md:hidden">
              <nav className="flex flex-col gap-3">
                {navItems.map((item) => (
                  <a key={item.href} href={item.href} className="py-2 text-sm font-medium" onClick={() => setMobileOpen(false)}>
                    {item.label}
                  </a>
                ))}
                <Link href="/login" className="py-2 text-sm font-medium" onClick={() => setMobileOpen(false)}>Sign In</Link>
                <Button asChild className="mt-2 bg-healthcare-green text-white hover:bg-healthcare-green-dark">
                  <a href="#contact" onClick={() => setMobileOpen(false)}>Request Demo</a>
                </Button>
              </nav>
            </div>
          )}
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="relative overflow-hidden border-b border-slate-200 bg-white">
          <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-green-50/70 to-transparent" />
          <div className="container relative mx-auto grid min-h-[calc(100vh-64px)] items-center gap-12 px-4 py-16 lg:grid-cols-[1.02fr_0.98fr] lg:py-20">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-green-200 bg-green-50 px-4 py-1.5 text-sm font-medium text-healthcare-green-dark">
                <HeartPulse className="h-4 w-4" />
                WHO Digital Health Guidelines Compliant
              </div>
              <h1 className="mt-6 max-w-4xl text-3xl font-bold tracking-tight sm:text-4xl md:text-6xl">
                AI-Powered Healthcare Platform for Zambia and Africa
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
                UbuntuCare helps hospitals, providers, public-health teams, and partners deliver connected care through clinical documentation AI, telemedicine, secure records, analytics, and medical knowledge support.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Button asChild size="xl" className="bg-healthcare-green text-white hover:bg-healthcare-green-dark">
                  <a href="#contact">Request Demo <ArrowRight className="ml-2 h-5 w-5" /></a>
                </Button>
                <Button asChild size="xl" variant="outline">
                  <a href="#features">Explore Platform</a>
                </Button>
              </div>
              <div className="mt-10 grid max-w-2xl grid-cols-3 gap-4 border-y border-slate-200 py-5">
                <div><p className="text-2xl font-bold text-healthcare-green">10</p><p className="text-xs font-medium text-slate-500">Zambian provinces in scope</p></div>
                <div><p className="text-2xl font-bold text-healthcare-blue">24/7</p><p className="text-xs font-medium text-slate-500">Care continuity workflows</p></div>
                <div><p className="text-2xl font-bold text-zambia-orange">AI</p><p className="text-xs font-medium text-slate-500">Built for clinical productivity</p></div>
              </div>
            </div>

            <div className="relative">
              <div className="rounded-lg border border-slate-200 bg-slate-950 p-3 shadow-2xl shadow-slate-200">
                <img src="/images/hero.png" alt="UbuntuCare AI-powered healthcare network" className="aspect-[16/10] w-full rounded-md" />
              </div>
              <div className="relative mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3 lg:absolute lg:-bottom-8 lg:left-6 lg:right-6 lg:mt-0 rounded-lg border border-slate-200 bg-white p-4 shadow-xl">
                {[['Clinical AI', 'SOAP notes'], ['Telemedicine', 'Remote care'], ['Analytics', 'Live insights']].map(([t, s]) => (
                  <div key={t}><p className="text-sm font-semibold">{t}</p><p className="text-xs text-slate-500">{s}</p></div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section id="features" className="bg-white py-20">
          <div className="container mx-auto px-4">
            <div className="max-w-3xl">
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Enterprise healthcare capabilities in one platform</h2>
              <p className="mt-4 text-lg leading-8 text-slate-600">UbuntuCare brings the core digital-health workflows into a single operating layer for clinicians, facilities, and health-system partners.</p>
            </div>
            <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
              {features.map(({ icon: Icon, title, text }) => (
                <article key={title} className="rounded-lg border border-slate-200 bg-white p-5 transition-shadow hover:shadow-lg">
                  <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-md bg-green-50 text-healthcare-green">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold">{title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Why Africa */}
        <section className="border-y border-slate-200 bg-green-50/60 py-20">
          <div className="container mx-auto grid gap-12 px-4 lg:grid-cols-[0.9fr_1.1fr]">
            <div>
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Why Africa&apos;s healthcare systems need a new digital foundation</h2>
              <p className="mt-5 text-lg leading-8 text-slate-600">Many facilities face high patient volumes, limited specialists, paper-heavy records, and fragmented reporting. UbuntuCare is designed for these operational realities, not for idealized healthcare environments.</p>
            </div>
            <div className="grid gap-4">
              {[
                'Support rural clinics with connected telemedicine and offline-aware workflows.',
                'Reduce documentation pressure on nurses, doctors, and clinical officers.',
                'Give hospitals live visibility into beds, queues, pharmacy stock, labs, and patient flow.',
                'Help ministries and partners detect disease trends earlier with structured data.',
              ].map((point) => (
                <div key={point} className="flex gap-4 rounded-lg border border-green-100 bg-white p-5">
                  <CheckCircle2 className="mt-1 h-5 w-5 flex-none text-healthcare-green" />
                  <p className="leading-7 text-slate-700">{point}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Security */}
        <section id="security" className="bg-white py-20">
          <div className="container mx-auto px-4">
            <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr]">
              <div>
                <ShieldCheck className="h-10 w-10 text-healthcare-blue" />
                <h2 className="mt-5 text-3xl font-bold tracking-tight md:text-4xl">Built for trust, privacy, and healthcare governance</h2>
                <p className="mt-5 text-lg leading-8 text-slate-600">UbuntuCare treats security as healthcare infrastructure: identity, access, auditability, and deployment controls are core to the product experience.</p>
              </div>
              <div className="grid gap-5 md:grid-cols-2">
                {trustItems.map(({ icon: Icon, title, text }) => (
                  <article key={title} className="rounded-lg border border-slate-200 p-5">
                    <Icon className="h-6 w-6 text-healthcare-green" />
                    <h3 className="mt-4 font-semibold">{title}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Partners */}
        <section className="bg-slate-950 py-20 text-white">
          <div className="container mx-auto px-4">
            <div className="max-w-3xl">
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Healthcare infrastructure for hospitals, governments, and partners</h2>
              <p className="mt-4 text-lg leading-8 text-slate-300">UbuntuCare is built for organizations that need reliable digital healthcare capacity across facilities, regions, and programs.</p>
            </div>
            <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
              {partners.map(({ icon: Icon, title, text }) => (
                <article key={title} className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
                  <Icon className="h-7 w-7 text-healthcare-green" />
                  <h3 className="mt-5 font-semibold">{title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing */}
        <section className="bg-white py-20">
          <div className="container mx-auto grid gap-10 px-4 lg:grid-cols-[0.85fr_1.15fr]">
            <div>
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Deployment models for serious healthcare partners</h2>
              <p className="mt-4 text-lg leading-8 text-slate-600">Pricing is scoped around facility size, deployment environment, integration needs, support requirements, and partner program goals.</p>
              <Button asChild className="mt-7 bg-healthcare-green text-white hover:bg-healthcare-green-dark">
                <a href="#contact">Discuss Deployment</a>
              </Button>
            </div>
            <div className="grid gap-4">
              {pricingTracks.map((track) => (
                <div key={track} className="flex items-center justify-between rounded-lg border border-slate-200 p-5">
                  <span className="font-semibold">{track}</span>
                  <ArrowRight className="h-5 w-5 text-healthcare-green" />
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Contact */}
        <section id="contact" className="border-y border-slate-200 bg-green-50/60 py-20">
          <div className="container mx-auto grid gap-12 px-4 lg:grid-cols-[1fr_1fr]">
            <div>
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Bring UbuntuCare to your healthcare organization</h2>
              <p className="mt-5 text-lg leading-8 text-slate-600">Request a focused conversation for hospital deployment, government partnership, academic research, NGO programs, or investor engagement.</p>
              <div className="mt-8 grid gap-4">
                <div className="flex items-center gap-3 text-slate-700"><MapPin className="h-5 w-5 text-healthcare-green" /> Plot 123, Great East Road, Lusaka, Zambia</div>
                <div className="flex items-center gap-3 text-slate-700"><Mail className="h-5 w-5 text-healthcare-green" /> Business: info@ubuntucare.zm</div>
                <div className="flex items-center gap-3 text-slate-700"><Mail className="h-5 w-5 text-healthcare-green" /> Support: support@ubuntucare.zm</div>
                <div className="flex items-center gap-3 text-slate-700"><Mail className="h-5 w-5 text-healthcare-green" /> Partnerships: partnerships@ubuntucare.zm</div>
                <div className="flex items-center gap-3 text-slate-700"><Phone className="h-5 w-5 text-healthcare-green" /> +260 211 123 456</div>
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-6">
              <h3 className="text-xl font-semibold">Request a demo</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">Tell us whether you represent a hospital, government agency, NGO, university, research group, or healthcare provider.</p>
              <div className="mt-6 grid gap-3">
                {['Hospital deployment', 'Government partnership', 'University or research collaboration', 'NGO or donor program', 'Provider pilot'].map((item) => (
                  <div key={item} className="flex items-center gap-3 rounded-md bg-slate-50 p-3 text-sm font-medium text-slate-700">
                    <CheckCircle2 className="h-4 w-4 text-healthcare-green" />
                    {item}
                  </div>
                ))}
              </div>
              <Button asChild size="xl" className="mt-6 w-full bg-healthcare-green text-white hover:bg-healthcare-green-dark">
                <a href="mailto:partnerships@ubuntucare.zm?subject=UbuntuCare%20Demo%20Request">Request Demo</a>
              </Button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-slate-950 py-14 text-white">
        <div className="container mx-auto px-4">
          <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-6">
            <div className="lg:col-span-2">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-healthcare-green">
                  <Heart className="h-5 w-5 text-white" fill="white" />
                </div>
                <div>
                  <p className="text-lg font-bold">UbuntuCare</p>
                  <p className="text-xs text-slate-400">Ubumi Bwakwe Bwikala Mu Zambia</p>
                </div>
              </div>
              <p className="mt-5 max-w-sm text-sm leading-6 text-slate-300">AI-powered healthcare infrastructure for connected care, clinical productivity, patient engagement, and public-health intelligence across Zambia and Africa.</p>
            </div>

            <div>
              <h4 className="font-semibold">Platform</h4>
              <ul className="mt-4 space-y-3 text-sm text-slate-400">
                <li><a href="#features" className="transition-colors hover:text-white">Clinical AI</a></li>
                <li><a href="#features" className="transition-colors hover:text-white">Secure EHR</a></li>
                <li><a href="#features" className="transition-colors hover:text-white">Telemedicine</a></li>
                <li><a href="#features" className="transition-colors hover:text-white">Analytics</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold">Policies</h4>
              <ul className="mt-4 space-y-3 text-sm text-slate-400">
                <li><Link href="/guidelines" className="transition-colors hover:text-white">Health Guidelines</Link></li>
                <li><Link href="/privacy" className="transition-colors hover:text-white">Privacy Policy</Link></li>
                <li><Link href="/terms" className="transition-colors hover:text-white">Terms & Conditions</Link></li>
                <li><Link href="/accessibility" className="transition-colors hover:text-white">Accessibility</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold">Resources</h4>
              <ul className="mt-4 space-y-3 text-sm text-slate-400">
                <li><Link href="/references" className="transition-colors hover:text-white">References</Link></li>
                <li><a href="#contact" className="transition-colors hover:text-white">Support</a></li>
                <li><a href="#contact" className="transition-colors hover:text-white">Partnerships</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold">Company</h4>
              <ul className="mt-4 space-y-3 text-sm text-slate-400">
                <li><span className="cursor-default">About Us</span></li>
                <li><span className="cursor-default">Careers</span></li>
                <li><a href="#contact" className="transition-colors hover:text-white">Contact</a></li>
              </ul>
            </div>
          </div>

          <div className="mt-10 flex flex-col justify-between gap-4 border-t border-white/10 pt-6 text-sm text-slate-400 md:flex-row">
            <p>&copy; {new Date().getFullYear()} UbuntuCare Zambia Limited. All rights reserved.</p>
            <div className="flex gap-5">
              <Link href="/privacy" className="underline underline-offset-2 hover:text-white">Privacy</Link>
              <Link href="/terms" className="underline underline-offset-2 hover:text-white">Terms</Link>
              <Link href="/accessibility" className="underline underline-offset-2 hover:text-white">Accessibility</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
