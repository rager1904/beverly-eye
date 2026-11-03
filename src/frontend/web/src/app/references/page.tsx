'use client';

import Link from 'next/link';
import { ArrowLeft, BookMarked, FileText, HeartPulse } from 'lucide-react';
import { Button } from '@/components/ui/button';

const referenceGroups = [
  {
    category: 'Government & Regulatory Frameworks',
    items: [
      'Zambia Data Protection Act No. 3 of 2021 — Parliament of Zambia.',
      'Zambia Ministry of Health — National e-Health Strategy 2020–2025.',
      'Zambia Ministry of Health — Electronic Health Record Framework and Standards (2022).',
      'Zambia Ministry of Health — Standard Treatment Guidelines, Essential Medicines List, and Essential Laboratory Supplies for Zambia (2023 Edition).',
      'Zambia Medicines Regulatory Authority (ZAMRA) — Guidelines for Digital Health Products and Software as a Medical Device.',
      'Zambia Information and Communications Technology Authority (ZICTA) — Cybersecurity and Data Protection Guidelines for Digital Health.',
      'Zambia Ministry of Health — Patients\' Charter of Rights and Responsibilities.',
    ],
  },
  {
    category: 'World Health Organization',
    items: [
      'WHO — Global Strategy on Digital Health 2020–2025.',
      'WHO — Classification of Digital Health Interventions v2.0 (WHO DHIC v2).',
      'WHO — Guidelines for the Safe Use of Artificial Intelligence in Healthcare (2023).',
      'WHO — Standards for Electronic Health Records in Low- and Middle-Income Countries.',
      'WHO Africa Region — Regional Strategy for Digital Health 2022–2030.',
      'WHO — Ethical Governance of Artificial Intelligence in Healthcare: Framework and Guidance.',
      'WHO — Patient Safety Guidelines and Clinical Risk Management in Digital Health.',
    ],
  },
  {
    category: 'International Standards & Technical References',
    items: [
      'ISO 27799:2016 — Health Informatics — Information Security Management in Health.',
      'ISO 27001:2022 — Information Security Management Systems — Requirements.',
      'ISO 13485:2016 — Medical Devices — Quality Management Systems.',
      'HL7 FHIR Release 4 — Health Level 7 International Standards for Health Data Exchange.',
      'ICD-10 — International Statistical Classification of Diseases and Related Health Problems, 10th Revision.',
      'SNOMED CT — Systematized Nomenclature of Medicine — Clinical Terms.',
      'LOINC — Logical Observation Identifiers Names and Codes.',
      'DICOM — Digital Imaging and Communications in Medicine.',
    ],
  },
  {
    category: 'Security & Compliance Frameworks',
    items: [
      'NIST SP 800-53 Rev. 5 — Security and Privacy Controls for Information Systems and Organizations.',
      'NIST SP 800-63B — Digital Identity Guidelines: Authentication and Lifecycle Management.',
      'OWASP Application Security Verification Standard (ASVS) v4.0.',
      'OWASP Top 10 Web Application Security Risks (2021).',
      'SOC 2 Type II — Trust Services Criteria for Security, Availability, and Confidentiality.',
      'GDPR (General Data Protection Regulation — EU 2016/679) — Applicable for international partner data.',
      'HIPAA Security Rule (45 CFR Part 160 and Subparts A and C of Part 164) — Reference framework.',
    ],
  },
  {
    category: 'Academic & Clinical Literature',
    items: [
      'The Lancet Digital Health — "Digital Health in Africa: Opportunities and Challenges" (2023).',
      'BMJ Global Health — "Artificial Intelligence for Clinical Decision Support in Resource-Limited Settings" (2024).',
      'Journal of Medical Internet Research (JMIR) — "Electronic Health Record Implementation in Sub-Saharan Africa: A Systematic Review" (2023).',
      'Nature Digital Medicine — "Large Language Models in Clinical Medicine: A Review of Applications and Limitations" (2024).',
      'PLOS Digital Health — "Telemedicine Adoption in Low- and Middle-Income Countries: Barriers and Enablers" (2023).',
      'WHO Bulletin — "Digital Transformation of Health Systems in the African Region" (2022).',
      'African Journal of Primary Health Care & Family Medicine — "Interoperability Standards for Health Information Exchange in SADC" (2023).',
    ],
  },
  {
    category: 'Zambia-Specific References',
    items: [
      'Republic of Zambia — The Constitution of Zambia (Amendment) Act No. 2 of 2016 — Right to Health.',
      'Republic of Zambia — Public Health Act, Cap 295 of the Laws of Zambia.',
      'Republic of Zambia — Mental Health Act No. 6 of 2019.',
      'Republic of Zambia — Medicines and Allied Substances Act, Cap 299.',
      'Republic of Zambia — Electronic Communications and Transactions Act No. 21 of 2021.',
      'Zambia National Public Health Institute (ZNPHI) — Integrated Disease Surveillance and Response (IDSR) Guidelines.',
      'Zambia Ministry of Health — National Health Insurance Scheme (NHIS) Operational Guidelines.',
      'Health Professions Council of Zambia (HPCZ) — Code of Ethics and Professional Conduct.',
    ],
  },
];

export default function ReferencesPage() {
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
              <BookMarked className="mx-auto h-10 w-10 text-healthcare-green" />
              <h1 className="mt-5 text-4xl font-bold tracking-tight md:text-5xl">References & Citations</h1>
              <p className="mt-4 text-lg leading-8 text-slate-600">
                UbuntuCare is built on established clinical, technical, and regulatory standards. The references below guide our design, compliance, and clinical safety frameworks and are reviewed quarterly to ensure alignment with the latest evidence and regulations.
              </p>
            </div>
          </div>
        </section>

        <section className="py-16">
          <div className="container mx-auto max-w-5xl px-4">
            <div className="grid gap-8 md:grid-cols-2">
              {referenceGroups.map((group) => (
                <div key={group.category} className="rounded-lg border border-slate-200 p-6">
                  <h2 className="font-semibold text-healthcare-green-dark">{group.category}</h2>
                  <ul className="mt-4 space-y-3">
                    {group.items.map((item) => (
                      <li key={item} className="flex gap-3 text-sm leading-6 text-slate-600">
                        <FileText className="mt-0.5 h-4 w-4 flex-none text-healthcare-green" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            <div className="mt-10 rounded-lg border border-green-100 bg-green-50/60 p-6 text-center">
              <p className="text-sm text-slate-600">
                For a complete list of references, standards, and regulatory filings, please contact{' '}
                <a href="mailto:compliance@ubuntucare.zm" className="font-medium text-healthcare-green underline underline-offset-2">compliance@ubuntucare.zm</a>.
                Citations are updated quarterly to reflect the latest WHO guidelines, Zambian regulations, and international standards.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-slate-950 py-10 text-white">
        <div className="container mx-auto px-4 text-center">
          <p className="text-sm text-slate-400">
            &copy; {new Date().getFullYear()} UbuntuCare Zambia Limited. &middot;
            <Link href="/privacy" className="ml-2 underline underline-offset-2 hover:text-white">Privacy</Link>
            <Link href="/terms" className="ml-4 underline underline-offset-2 hover:text-white">Terms</Link>
            <Link href="/" className="ml-4 underline underline-offset-2 hover:text-white">Home</Link>
          </p>
        </div>
      </footer>
    </div>
  );
}
