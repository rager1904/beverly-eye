'use client';

import Link from 'next/link';
import { ArrowLeft, ShieldCheck, HeartPulse } from 'lucide-react';
import { Button } from '@/components/ui/button';

const sections = [
  {
    id: 'collection', title: '1. Data We Collect',
    content: 'We collect the minimum data necessary to deliver safe healthcare: name, contact details, date of birth, national ID (where required), medical history, diagnoses, medications, laboratory results, vital signs, and insurance information. We also collect account credentials and usage logs for security and audit purposes. Sensitive health data is only collected with explicit, informed consent and is never used for purposes beyond direct care, public health reporting (de-identified), and regulatory compliance.',
  },
  {
    id: 'usage', title: '2. How We Use Your Data',
    content: 'Data is used exclusively for: providing clinical care, coordinating appointments and referrals, managing pharmacy and laboratory workflows, generating de-identified public-health analytics, improving platform functionality and user experience, and meeting legal and regulatory obligations as required by Zambian law. We do not use patient data for advertising, profiling, or any commercial purpose unrelated to healthcare delivery.',
  },
  {
    id: 'sharing', title: '3. Data Sharing & Disclosure',
    content: 'We do not sell, rent, or trade patient data. Data may be shared with: healthcare providers involved in your care (with your explicit consent), the Zambian Ministry of Health for statutory public-health reporting (de-identified aggregate data only), third-party systems you authorize through separate, granular consent (e.g., national insurance systems, referral hospitals), and law enforcement agencies only when required by the laws of the Republic of Zambia. Any data sharing with international partners is governed by standard contractual clauses and adequacy decisions under the Zambia Data Protection Act.',
  },
  {
    id: 'retention', title: '4. Data Retention & Deletion',
    content: 'Health records are retained for the period specified by Zambian healthcare regulations and the Zambia Ministry of Health record-keeping guidelines. After the statutory retention period expires, data is securely deleted or irreversibly de-identified. Account data is retained until account closure, subject to any legal holds or ongoing care obligations. Patients may request earlier deletion of their data, subject to legal and clinical retention requirements.',
  },
  {
    id: 'rights', title: '5. Your Rights',
    content: 'Under the Zambia Data Protection Act No. 3 of 2021, you have the following rights: right to access your personal data, right to rectify inaccurate data, right to erasure (subject to legal holds), right to restrict processing, right to data portability in a structured, machine-readable format, right to object to processing, and right to withdraw consent at any time without affecting the lawfulness of processing before withdrawal. To exercise these rights, contact our Data Protection Officer at dpo@ubuntucare.zm.',
  },
  {
    id: 'cookies', title: '6. Cookies & Tracking Technologies',
    content: 'We use essential cookies for authentication, session management, and platform security. These cookies are strictly necessary for the platform to function. Analytics cookies and preference cookies are used only with your explicit consent. You can manage your cookie preferences at any time through your account settings. We do not use advertising cookies, third-party tracking cookies, or any form of cross-site tracking. For detailed cookie information, contact dpo@ubuntucare.zm.',
  },
  {
    id: 'security', title: '7. Data Security Measures',
    content: 'All data in transit is encrypted using TLS 1.3. Data at rest is encrypted using AES-256. Access to patient data is strictly role-based, with granular permissions mapped to clinical roles (provider, nurse, lab tech, pharmacist, etc.). Every access event is logged to an immutable audit trail. We conduct annual security audits by independent third parties, regular penetration testing, and mandatory data protection training for all staff. Our infrastructure is monitored 24/7 for security events.',
  },
  {
    id: 'breach', title: '8. Data Breach Notification',
    content: 'In the event of a data breach that affects personal health information, we will: contain and remediate the breach within 24 hours, notify the Zambian Data Protection Commissioner within 72 hours as required by law, notify all affected individuals without undue delay, provide clear information about the nature of the breach and steps taken, and offer credit monitoring or identity protection services where appropriate. Our incident response plan is tested quarterly.',
  },
  {
    id: 'international', title: '9. International Data Transfers',
    content: 'If patient data is transferred outside Zambia, such transfers are governed by: standard contractual clauses approved by the Zambian Data Protection Commissioner, adequacy decisions recognizing equivalent data protection in the recipient country, and explicit patient consent where required. We maintain a register of all international data transfers and conduct periodic Data Protection Impact Assessments (DPIAs) for cross-border data flows.',
  },
  {
    id: 'children', title: '10. Children&apos;s Privacy',
    content: 'UbuntuCare may process health data of minors (individuals under 18 years) only with the explicit consent of a parent or legal guardian. We collect the minimum data necessary for the child\'s healthcare. Parents or guardians have the right to access, correct, and request deletion of their child\'s health data. We do not knowingly process data of children for any purpose other than direct healthcare delivery.',
  },
  {
    id: 'changes', title: '11. Changes to This Policy',
    content: 'We may update this Privacy Policy to reflect changes in legal requirements, platform capabilities, or operational practices. Material changes will be communicated via: email notification to the account holder, a notice on the platform dashboard at least 30 days before the change takes effect, and where appropriate, separate consent for new data processing activities. Continued use of the platform after changes take effect constitutes acceptance of the updated policy.',
  },
  {
    id: 'contact', title: '12. Contact & Complaints',
    content: 'For questions, concerns, or complaints about this Privacy Policy or our data practices, contact: Data Protection Officer — dpo@ubuntucare.zm. Physical address: Plot 123, Great East Road, Lusaka, Zambia. You also have the right to lodge a complaint with the Zambia Data Protection Commissioner at info@dataprotection.zm or +260 211 123 789.',
  },
];

export default function PrivacyPage() {
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
              <ShieldCheck className="mx-auto h-10 w-10 text-healthcare-green" />
              <h1 className="mt-5 text-4xl font-bold tracking-tight md:text-5xl">Privacy Policy</h1>
              <p className="mt-4 text-lg leading-8 text-slate-600">
                Last updated: July 2026. This Privacy Policy explains how UbuntuCare (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) collects, uses, stores, and protects your personal and health data when you use our platform. We are committed to protecting your privacy in accordance with the Zambia Data Protection Act No. 3 of 2021 and applicable international standards.
              </p>
            </div>
          </div>
        </section>

        <section className="py-16">
          <div className="container mx-auto max-w-4xl px-4">
            {/* Table of Contents */}
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-6">
              <h2 className="font-semibold">Table of Contents</h2>
              <nav className="mt-4 grid gap-2 sm:grid-cols-2">
                {sections.map((s) => (
                  <a key={s.id} href={`#${s.id}`} className="text-sm text-slate-600 transition-colors hover:text-healthcare-green">
                    {s.title}
                  </a>
                ))}
              </nav>
            </div>

            {/* Sections */}
            <div className="mt-12 space-y-10">
              {sections.map((s) => (
                <div key={s.id} id={s.id}>
                  <h3 className="text-xl font-semibold">{s.title}</h3>
                  <p className="mt-3 leading-7 text-slate-600">{s.content}</p>
                </div>
              ))}
            </div>

            {/* Contact Block */}
            <div className="mt-12 rounded-lg border border-green-100 bg-green-50/60 p-6">
              <p className="font-semibold">Data Protection Officer</p>
              <p className="mt-2 text-sm text-slate-600">Email: dpo@ubuntucare.zm</p>
              <p className="text-sm text-slate-600">Zambia Data Protection Commissioner: info@dataprotection.zm</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-slate-950 py-10 text-white">
        <div className="container mx-auto px-4 text-center">
          <p className="text-sm text-slate-400">
            &copy; {new Date().getFullYear()} UbuntuCare Zambia Limited. &middot;
            <Link href="/terms" className="ml-2 underline underline-offset-2 hover:text-white">Terms & Conditions</Link>
            <Link href="/" className="ml-4 underline underline-offset-2 hover:text-white">Home</Link>
          </p>
        </div>
      </footer>
    </div>
  );
}
