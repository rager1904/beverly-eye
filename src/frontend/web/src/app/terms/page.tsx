'use client';

import Link from 'next/link';
import { ArrowLeft, Award, FileText, Globe2, HeartPulse, Scale, Shield, UserCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';

const highlights = [
  { icon: UserCheck, title: 'Account Responsibility', text: 'You are responsible for maintaining the confidentiality of your login credentials and for all activities under your account.' },
  { icon: Shield, title: 'Acceptable Use', text: 'The platform may only be used for lawful healthcare purposes. Misuse, abuse, or unauthorised access is strictly prohibited.' },
  { icon: Scale, title: 'Limitation of Liability', text: 'UbuntuCare is a clinical support tool. Clinicians retain full responsibility for patient care decisions. See full terms for details.' },
  { icon: FileText, title: 'Service Availability', text: 'We strive for 99.9% uptime but do not guarantee uninterrupted service. Maintenance windows are scheduled and communicated in advance.' },
  { icon: Award, title: 'Intellectual Property', text: 'The platform, its code, design, and content are protected by copyright and intellectual property laws.' },
  { icon: Globe2, title: 'Governing Law', text: 'These terms are governed by the laws of the Republic of Zambia. Disputes shall be resolved through arbitration in Lusaka.' },
];

const clauses = [
  {
    num: '1', title: 'Acceptance of Terms',
    content: 'By creating an account, accessing, or using UbuntuCare ("the Platform"), you agree to be bound by these Terms & Conditions. If you do not agree to all of these terms, do not use the Platform. If you are using the Platform on behalf of a healthcare facility, organization, or government entity, you represent that you have the legal authority to bind that entity to these terms. These terms constitute a legally binding agreement between you (or your organization) and UbuntuCare Zambia Limited.',
  },
  {
    num: '2', title: 'License Grant',
    content: 'Subject to your compliance with these terms, we grant you a limited, non-exclusive, non-transferable, revocable license to access and use the Platform for lawful healthcare purposes. This license does not include: the right to sublicense, sell, or commercially exploit the Platform; the right to modify, reverse-engineer, or create derivative works; or access granted for purposes that compete with UbuntuCare. All rights not expressly granted are reserved by UbuntuCare Zambia Limited.',
  },
  {
    num: '3', title: 'User Obligations & Prohibited Conduct',
    content: 'You agree to: maintain the confidentiality of your account credentials; provide accurate, current, and complete information; use the Platform in compliance with all applicable Zambian laws and healthcare regulations; promptly report any security incidents or unauthorized access. You may not: access or attempt to access unauthorized areas of the Platform; transmit malware, viruses, or harmful code; use the Platform for any unlawful purpose; interfere with the operation, security, or integrity of the Platform; impersonate any person or entity; or use the Platform to store or transmit illegal content.',
  },
  {
    num: '4', title: 'Medical Disclaimer',
    content: 'The Platform is a clinical documentation and decision-support tool. It is not a substitute for professional medical judgment, diagnosis, or treatment. Healthcare providers retain full, independent responsibility for all clinical decisions, diagnoses, treatments, and patient outcomes. AI-generated outputs, summaries, and suggestions must be reviewed and validated by a qualified clinician before use in patient care. The Platform does not provide emergency medical services. In case of a medical emergency, contact local emergency services immediately. UbuntuCare makes no guarantees regarding the completeness, accuracy, or reliability of AI-generated clinical content.',
  },
  {
    num: '5', title: 'Data Protection & Privacy',
    content: 'Use of the Platform is subject to our Privacy Policy, which is incorporated into these terms by reference. Both parties agree to comply with the Zambia Data Protection Act No. 3 of 2021. UbuntuCare serves as a data processor for healthcare organizations that act as data controllers. Data processing agreements are available upon request. Patient health data is handled in accordance with our Privacy Policy and applicable data protection laws.',
  },
  {
    num: '6', title: 'Intellectual Property Rights',
    content: 'The Platform, including its source code, design, architecture, interfaces, content, trademarks, and branding, is the exclusive property of UbuntuCare Zambia Limited and is protected by Zambian and international intellectual property laws. You retain all rights to your data and content you enter into the Platform. We claim no ownership over patient health data entered into the system. Feedback or suggestions you provide may be used to improve the Platform without compensation.',
  },
  {
    num: '7', title: 'Service Level & Availability',
    content: 'We strive to maintain 99.9% Platform availability, excluding scheduled maintenance. Maintenance windows are scheduled between 00:00 and 04:00 CAT and communicated at least 48 hours in advance. Emergency maintenance may be performed with shorter notice. We do not guarantee uninterrupted or error-free operation. The Platform may be temporarily unavailable due to factors beyond our reasonable control, including internet outages, force majeure events, or third-party service disruptions.',
  },
  {
    num: '8', title: 'Limitation of Liability',
    content: 'To the maximum extent permitted by Zambian law: UbuntuCare shall not be liable for indirect, incidental, special, consequential, or punitive damages arising from your use of the Platform. Our total liability for any claim arising from these terms or Platform use shall not exceed the total fees paid by you in the twelve (12) months preceding the claim. This limitation applies whether the claim is in contract, tort (including negligence), strict liability, or otherwise. Nothing in these terms excludes or limits liability for death or personal injury caused by negligence, fraud, or any other liability that cannot be excluded by Zambian law.',
  },
  {
    num: '9', title: 'Termination',
    content: 'We may suspend or terminate your access to the Platform: for breach of these terms; for extended inactivity exceeding 12 months; at your written request; or as required by law or regulatory authority. Upon termination: your right to access the Platform ceases immediately; you must export your data within 30 days (after which it will be securely deleted subject to legal holds); obligations regarding confidentiality, intellectual property, and limitation of liability survive termination.',
  },
  {
    num: '10', title: 'Indemnification',
    content: 'You agree to indemnify, defend, and hold harmless UbuntuCare Zambia Limited, its officers, directors, employees, and agents from any claims, damages, losses, liabilities, and expenses arising from: your use of the Platform in violation of these terms; your violation of any law or third-party right; any content you submit to the Platform; or your violation of applicable healthcare regulations.',
  },
  {
    num: '11', title: 'Governing Law & Dispute Resolution',
    content: 'These terms are governed by the laws of the Republic of Zambia. Any dispute arising from these terms shall first be resolved through good-faith negotiation between the parties. If unresolved within 30 days, disputes shall be finally settled by binding arbitration in Lusaka, Zambia, in accordance with the Zambian Arbitration Act No. 19 of 2000. The arbitration shall be conducted in English by a single arbitrator appointed by the parties or, failing agreement, by the Zambia Association of Arbitration. Each party bears its own arbitration costs unless the arbitrator determines otherwise.',
  },
  {
    num: '12', title: 'Changes to Terms',
    content: 'We reserve the right to modify these terms at any time. Material changes will be communicated via: email to the registered account address; platform notification at login; and at least 30 days\' notice before the effective date. Continued use of the Platform after changes take effect constitutes acceptance of the modified terms. If you do not agree to the changes, you must stop using the Platform and request account closure. Minor changes (typos, clarifications, contact updates) may take effect immediately.',
  },
  {
    num: '13', title: 'Miscellaneous',
    content: 'These terms constitute the entire agreement between you and UbuntuCare regarding Platform use. If any provision is found unenforceable, the remaining provisions remain in full effect. Failure to enforce any right does not constitute a waiver. You may not assign these terms without our written consent. We may assign these terms in connection with a merger, acquisition, or sale of assets. Notices shall be sent to the email address on your account or to legal@ubuntucare.zm.',
  },
];

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-white text-slate-950">
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
        <section className="border-b border-slate-200 bg-gradient-to-b from-green-50/80 to-white py-16">
          <div className="container mx-auto px-4 text-center">
            <div className="mx-auto max-w-3xl">
              <Scale className="mx-auto h-10 w-10 text-healthcare-green" />
              <h1 className="mt-5 text-4xl font-bold tracking-tight md:text-5xl">Terms & Conditions</h1>
              <p className="mt-4 text-lg leading-8 text-slate-600">
                Last updated: July 2026. By accessing or using UbuntuCare, you agree to be bound by these Terms & Conditions. Please read them carefully.
              </p>
            </div>
          </div>
        </section>

        {/* Highlights */}
        <section className="border-b border-slate-200 bg-white py-12">
          <div className="container mx-auto px-4">
            <h2 className="text-center text-lg font-semibold text-slate-500">Key Points Summary</h2>
            <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {highlights.map(({ icon: Icon, title, text }) => (
                <div key={title} className="rounded-lg border border-slate-200 p-4">
                  <Icon className="h-5 w-5 text-healthcare-green" />
                  <h3 className="mt-3 font-semibold">{title}</h3>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Full Terms */}
        <section className="py-16">
          <div className="container mx-auto max-w-4xl px-4">
            <h2 className="text-2xl font-bold">Full Terms of Use</h2>
            <div className="mt-8 space-y-8">
              {clauses.map((c) => (
                <div key={c.num} id={`clause-${c.num}`}>
                  <h3 className="text-lg font-semibold">Clause {c.num}: {c.title}</h3>
                  <p className="mt-2 leading-7 text-slate-600">{c.content}</p>
                </div>
              ))}
            </div>

            <div className="mt-12 rounded-lg border border-green-100 bg-green-50/60 p-6">
              <p className="font-semibold">Contact</p>
              <p className="mt-2 text-sm text-slate-600">For questions about these terms: legal@ubuntucare.zm</p>
              <p className="text-sm text-slate-600">UbuntuCare Zambia Limited, Plot 123, Great East Road, Lusaka, Zambia</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-slate-950 py-10 text-white">
        <div className="container mx-auto px-4 text-center">
          <p className="text-sm text-slate-400">
            &copy; {new Date().getFullYear()} UbuntuCare Zambia Limited. &middot;
            <Link href="/privacy" className="ml-2 underline underline-offset-2 hover:text-white">Privacy Policy</Link>
            <Link href="/" className="ml-4 underline underline-offset-2 hover:text-white">Home</Link>
          </p>
        </div>
      </footer>
    </div>
  );
}
