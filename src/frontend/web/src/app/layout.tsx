import type { Metadata, Viewport } from 'next';
import './globals.css';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'UbuntuCare - Zambia Health Platform',
  description: 'Connected healthcare platform for Zambia. Patient management, EMR, telemedicine, and public health surveillance.',
  keywords: ['healthcare', 'Zambia', 'EMR', 'telemedicine', 'public health'],
  authors: [{ name: 'UbuntuCare' }],
  manifest: '/manifest.json',
  icons: { icon: '/favicon.ico', apple: '/apple-icon.png' },
  openGraph: {
    title: 'UbuntuCare - Zambia',
    description: 'Connected healthcare platform for Zambia',
    type: 'website',
    locale: 'en_ZM',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#22c55e',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
