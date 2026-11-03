'use client';

import Link from 'next/link';
import { ArrowLeft, Eye, HeartPulse, Keyboard, Languages, Monitor, Type } from 'lucide-react';
import { Button } from '@/components/ui/button';

const standards = [
  { icon: Eye, title: 'Perceivable', text: 'All non-text content has text alternatives. Captions are provided for multimedia. Content can be presented in different ways without losing meaning. Colour is not used as the only means of conveying information. Sufficient colour contrast ratios are maintained throughout the platform.' },
  { icon: Keyboard, title: 'Operable', text: 'All functionality is available from a keyboard. Users are given enough time to read and use content. Content does not cause seizures or physical reactions. Users can navigate and find content easily. Input modalities beyond keyboard are supported.' },
  { icon: Languages, title: 'Understandable', text: 'Text content is readable and understandable. Web pages appear and operate in predictable ways. Users are helped to avoid and correct mistakes. Clear labels, instructions, and error messages are provided. Content is available in multiple Zambian languages.' },
  { icon: Monitor, title: 'Robust', text: 'Content is compatible with current and future user agents, including assistive technologies. Semantic HTML is used throughout. ARIA landmarks and roles are properly implemented. The platform is tested with major screen readers and assistive tools.' },
];

const compliance = [
  'Conformance target: WCAG 2.1 Level AA (W3C Web Content Accessibility Guidelines).',
  'Additional targets: WCAG 2.2 Level AA compliance planned by Q1 2027.',
  'Platform tested with: NVDA, JAWS, VoiceOver, and Windows Narrator screen readers.',
  'Keyboard navigation: all interactive elements are reachable and operable via keyboard alone.',
  'Colour contrast: minimum ratio of 4.5:1 for normal text and 3:1 for large text.',
  'Text resizing: content is readable when zoomed to 200% without loss of functionality.',
  'Focus indicators: visible focus styles are provided for all interactive elements.',
  'Skip navigation: a "Skip to main content" link is provided on all pages.',
  'Multilingual support: platform interface is available in English, Chibemba, Chinyanja, Chitonga, and Silozi.',
];

export default function AccessibilityPage() {
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
              <Eye className="mx-auto h-10 w-10 text-healthcare-green" />
              <h1 className="mt-5 text-4xl font-bold tracking-tight md:text-5xl">Accessibility Statement</h1>
              <p className="mt-4 text-lg leading-8 text-slate-600">
                UbuntuCare is committed to ensuring digital accessibility for all users, including those with disabilities. We continuously work to conform to WCAG 2.1 Level AA standards and Zambian accessibility guidelines.
              </p>
            </div>
          </div>
        </section>

        {/* Standards */}
        <section className="py-16">
          <div className="container mx-auto max-w-5xl px-4">
            <h2 className="text-2xl font-bold">Our Accessibility Standards</h2>
            <div className="mt-8 grid gap-6 md:grid-cols-2">
              {standards.map(({ icon: Icon, title, text }) => (
                <div key={title} className="rounded-lg border border-slate-200 p-6">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-green-50 text-healthcare-green">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="text-lg font-semibold">{title}</h3>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-slate-600">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Compliance */}
        <section className="border-y border-slate-200 bg-green-50/60 py-16">
          <div className="container mx-auto max-w-4xl px-4">
            <h2 className="text-2xl font-bold">Compliance & Testing</h2>
            <div className="mt-8 grid gap-4 md:grid-cols-2">
              {compliance.map((item) => (
                <div key={item} className="flex items-start gap-3 rounded-lg border border-green-100 bg-white p-4">
                  <Type className="mt-0.5 h-4 w-4 flex-none text-healthcare-green" />
                  <p className="text-sm leading-6 text-slate-600">{item}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Limitations */}
        <section className="py-16">
          <div className="container mx-auto max-w-4xl px-4">
            <h2 className="text-2xl font-bold">Known Limitations</h2>
            <p className="mt-4 leading-7 text-slate-600">
              While we strive for full accessibility, some areas of the platform are under active improvement:
            </p>
            <ul className="mt-4 space-y-2 text-sm leading-6 text-slate-600">
              <li className="flex gap-3"><span className="text-healthcare-green">&bull;</span> Some legacy dashboard components may have incomplete ARIA labels — these are being remediated in our current sprint cycle.</li>
              <li className="flex gap-3"><span className="text-healthcare-green">&bull;</span> Real-time telemedicine video components rely on third-party libraries that may have varying levels of accessibility support.</li>
              <li className="flex gap-3"><span className="text-healthcare-green">&bull;</span> AI-generated clinical summaries are text-based and screen-reader compatible, but voice interaction features are still in development.</li>
              <li className="flex gap-3"><span className="text-healthcare-green">&bull;</span> Some PDF reports generated by the platform may require additional accessibility processing.</li>
            </ul>
          </div>
        </section>

        {/* Feedback */}
        <section className="border-t border-slate-200 bg-slate-950 py-14 text-white">
          <div className="container mx-auto px-4 text-center">
            <h2 className="text-2xl font-bold">Accessibility Feedback</h2>
            <p className="mt-4 text-slate-300">
              We welcome your feedback on the accessibility of UbuntuCare. Please let us know if you encounter accessibility barriers.
            </p>
            <div className="mt-4 text-sm text-slate-400">
              <p>Email: <a href="mailto:accessibility@ubuntucare.zm" className="text-healthcare-green underline underline-offset-2">accessibility@ubuntucare.zm</a></p>
              <p className="mt-1">We aim to respond to accessibility feedback within 5 business days.</p>
            </div>
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
          <p>&copy; {new Date().getFullYear()} UbuntuCare Zambia Limited. <Link href="/privacy" className="underline hover:text-slate-950">Privacy</Link> &middot; <Link href="/terms" className="underline hover:text-slate-950">Terms</Link> &middot; <Link href="/guidelines" className="underline hover:text-slate-950">Guidelines</Link></p>
        </div>
      </footer>
    </div>
  );
}
