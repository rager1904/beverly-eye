'use client';

import Link from 'next/link';
import {
  ArrowLeft, BookMarked, CheckCircle2, Eye, FileCheck,
  HeartPulse, LockKeyhole, ScrollText, Shield, ShieldCheck,
  UserCheck, X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const guidelineTopics = [
  {
    icon: HeartPulse, title: 'Clinical Safety',
    items: [
      'All clinical AI outputs are clearly marked as assistive — clinicians retain full decision-making authority.',
      'UbuntuCare follows WHO digital health intervention guidelines (WHO DHIC v2) for safe AI-assisted care.',
      'Patient data is never used to train models without explicit, informed consent from the patient or guardian.',
      'Alert fatigue is minimised through clinically validated, tiered notification systems.',
    ],
  },
  {
    icon: UserCheck, title: 'Data Privacy & Consent',
    items: [
      'Patient health information is collected, stored, and processed in compliance with the Zambia Data Protection Act No. 3 of 2021.',
      'Explicit, informed consent is obtained before any patient data is entered into the system.',
      'Patients have the right to access, correct, and request deletion of their personal health data.',
      'Data sharing with third-party systems requires separate, granular consent from the patient.',
    ],
  },
  {
    icon: Shield, title: 'Infection Prevention & Control',
    items: [
      'Telemedicine workflows follow Zambia Ministry of Health IPC guidelines for remote consultations.',
      'Laboratory ordering and results workflows include biohazard and infection risk flagging.',
      'Inventory management tracks PPE, sterilization supplies, and infection control stock levels.',
      'Patient queue and appointment scheduling supports social distancing and cohort management.',
    ],
  },
  {
    icon: BookMarked, title: 'Clinical Documentation Standards',
    items: [
      'All clinical notes comply with the Zambia Electronic Health Record standards (MOH EHR Framework 2022).',
      'SOAP note structure follows international clinical documentation best practices adapted for Zambian protocols.',
      'Medication prescriptions use the Zambia Essential Medicines List (EML) and Standard Treatment Guidelines.',
      'ICD-10 and CPT coding are supported for diagnosis and procedure documentation.',
    ],
  },
];

const patientRights = [
  { icon: Eye, title: 'Right to Access', text: 'Patients may request and receive a copy of their health records within the timelines stipulated by Zambian law.' },
  { icon: LockKeyhole, title: 'Right to Confidentiality', text: 'All patient health information is protected by encryption, access controls, and strict confidentiality agreements.' },
  { icon: FileCheck, title: 'Right to Informed Consent', text: 'No clinical procedure or data processing occurs without the patient\'s freely given, informed consent.' },
  { icon: ShieldCheck, title: 'Right to Data Portability', text: 'Patients may request transfer of their health data to another provider or system in a structured, machine-readable format.' },
  { icon: ScrollText, title: 'Right to Correction', text: 'Patients may request correction of inaccurate, incomplete, or outdated personal health information.' },
  { icon: X, title: 'Right to Withdraw Consent', text: 'Patients may withdraw consent for data processing at any time, subject to legal and clinical retention requirements.' },
];

export default function GuidelinesPage() {
  return (
    <div className="min-h-screen bg-white text-slate-950">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2 text-sm font-medium text-slate-600 transition-colors hover:text-slate-950">
            <ArrowLeft className="h-4 w-4" />
            Back to Home
          </Link>
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-healthcare-green">
              <HeartPulse className="h-4 w-4 text-white" />
            </div>
            <span className="text-sm font-bold">UbuntuCare</span>
          </Link>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="border-b border-slate-200 bg-gradient-to-b from-green-50/80 to-white py-16">
          <div className="container mx-auto px-4 text-center">
            <div className="mx-auto max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-green-200 bg-white px-4 py-1.5 text-sm font-medium text-healthcare-green-dark">
                <HeartPulse className="h-4 w-4" />
                Clinical Safety & Regulatory Compliance
              </div>
              <h1 className="mt-6 text-4xl font-bold tracking-tight md:text-5xl">Health Guidelines & Clinical Standards</h1>
              <p className="mt-4 text-lg leading-8 text-slate-600">
                UbuntuCare operates within established clinical safety frameworks, data protection regulations, and international health informatics standards. Every feature is designed with patient safety and regulatory compliance as foundational requirements.
              </p>
            </div>
          </div>
        </section>

        {/* Guidelines */}
        <section className="py-16">
          <div className="container mx-auto px-4">
            <div className="grid gap-8 md:grid-cols-2">
              {guidelineTopics.map(({ icon: Icon, title, items }) => (
                <div key={title} className="rounded-lg border border-slate-200 p-6">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-green-50 text-healthcare-green">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h2 className="text-lg font-semibold">{title}</h2>
                  </div>
                  <ul className="mt-5 space-y-3">
                    {items.map((item) => (
                      <li key={item} className="flex gap-3 text-sm leading-6 text-slate-600">
                        <CheckCircle2 className="mt-0.5 h-4 w-4 flex-none text-healthcare-green" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Medical Disclaimer */}
        <section className="border-y border-slate-200 bg-green-50/60 py-16">
          <div className="container mx-auto px-4">
            <div className="mx-auto max-w-4xl">
              <div className="rounded-lg border border-green-100 bg-white p-6 md:p-8">
                <div className="flex items-start gap-4">
                  <ScrollText className="mt-1 h-6 w-6 flex-none text-healthcare-green" />
                  <div>
                    <h2 className="text-xl font-semibold">Medical Disclaimer</h2>
                    <div className="mt-4 space-y-4 text-sm leading-6 text-slate-600">
                      <p>UbuntuCare is a clinical support tool. It does not replace the independent clinical judgment of licensed healthcare professionals.</p>
                      <p>All AI-generated outputs must be reviewed and validated by a qualified clinician before being used in patient care decisions. Clinicians remain fully responsible for diagnosis, treatment, and clinical outcomes.</p>
                      <p>In case of a medical emergency, please contact your local emergency services immediately. The platform is not designed for emergency response.</p>
                      <p>The platform may contain summaries, suggestions, and documentation aids generated by artificial intelligence. These outputs may contain inaccuracies or omissions and should always be cross-checked against original sources and professional judgment.</p>
                      <p>UbuntuCare makes no warranties, express or implied, regarding the completeness, accuracy, or reliability of AI-generated content for clinical decision-making.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Patient Rights */}
        <section className="py-16">
          <div className="container mx-auto px-4">
            <div className="mx-auto max-w-3xl text-center">
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Patient Rights & Responsibilities</h2>
              <p className="mt-4 text-lg leading-8 text-slate-600">
                UbuntuCare respects and protects the fundamental rights of every patient. These rights are aligned with the Zambian Patients&apos; Charter and international healthcare ethics standards.
              </p>
            </div>
            <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {patientRights.map(({ icon: Icon, title, text }) => (
                <div key={title} className="rounded-lg border border-slate-200 p-5">
                  <Icon className="h-6 w-6 text-healthcare-green" />
                  <h3 className="mt-4 font-semibold">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="border-t border-slate-200 bg-slate-950 py-14 text-center text-white">
          <div className="container mx-auto px-4">
            <h2 className="text-2xl font-bold">Committed to safe, ethical, and compliant healthcare technology</h2>
            <p className="mt-3 text-slate-300">Our guidelines are reviewed quarterly and align with the latest WHO, MOH, and international standards.</p>
            <div className="mt-6 flex justify-center gap-4">
              <Button asChild variant="outline" className="border-white/20 text-white hover:bg-white/10">
                <Link href="/references">View References</Link>
              </Button>
              <Button asChild className="bg-healthcare-green text-white hover:bg-healthcare-green-dark">
                <Link href="/">Back to Home</Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white py-8">
        <div className="container mx-auto px-4 text-center text-sm text-slate-500">
          <p>&copy; {new Date().getFullYear()} UbuntuCare Zambia Limited. <Link href="/privacy" className="underline hover:text-slate-950">Privacy</Link> &middot; <Link href="/terms" className="underline hover:text-slate-950">Terms</Link></p>
        </div>
      </footer>
    </div>
  );
}
