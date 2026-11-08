const withPWA = require('next-pwa')({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true,
  // Let an open session finish before a new worker takes control. This avoids
  // swapping page/network behavior during a clinical workflow.
  skipWaiting: false,
  clientsClaim: false,
  // Restoring network connectivity must not discard an in-progress form.
  reloadOnOnline: false,
  // Remove old versions' cached API/route data when the replacement worker
  // activates; those caches may contain patient-specific responses.
  importScripts: ['/clear-sensitive-caches.js'],
  runtimeCaching: [
    {
      urlPattern: /^https?.*\/api\/v1\/.*/i,
      // Clinical and authentication responses must never be replayed from a
      // browser cache when the API is slow or unavailable.
      handler: 'NetworkOnly',
    },
    {
      urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/i,
      handler: 'CacheFirst',
      options: { cacheName: 'image-cache', expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 * 30 } },
    },
    {
      urlPattern: /^https?.*/i,
      handler: 'NetworkOnly',
    },
  ],
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  swcMinify: true,
  compiler: { removeConsole: process.env.NODE_ENV === 'production' },
  async rewrites() {
    const apiInternal = (process.env.API_INTERNAL_URL || 'http://localhost:8000').replace(/\/$/, '');
    return [
      {
        source: '/api/v1/:path*',
        destination: `${apiInternal}/api/v1/:path*`,
      },
    ];
  },
  experimental: {
    optimizePackageImports: ['lucide-react', 'recharts', 'date-fns'],
  },
  headers: async () => [
    {
      source: '/(.*)',
      headers: [
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'X-XSS-Protection', value: '1; mode=block' },
        { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
      ],
    },
  ],
};

module.exports = withPWA(nextConfig);
