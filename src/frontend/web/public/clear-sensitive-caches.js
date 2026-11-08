const sensitiveRuntimeCaches = new Set(['api-cache', 'offline-cache', 'next-data', 'others']);

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames
          .filter((cacheName) => sensitiveRuntimeCaches.has(cacheName))
          .map((cacheName) => caches.delete(cacheName))
      )
    )
  );
});
