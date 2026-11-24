// Offline service worker for the journal reader (journal-handwritten-web #29).
//
// Cache policy, by design:
// - The handwriting font (fonts/handwriting.woff2) is immutable content:
//   cache-first, and a font change ships with a CACHE_VERSION bump, so a
//   stale font can never outlive its version.
// - Page scans (img/**) are content-stable (MANIFEST.sha256 checksums them):
//   stale-while-revalidate, so a held page stays readable offline and
//   refreshes in the background.
// - Everything else (index.html, site/data/j.json, studio data): network-first
//   and never cached by this worker, so a stale app shell or stale readings
//   can never be served from the offline cache.
// - Only same-origin GET requests are handled. Cross-origin and non-GET
//   requests pass through untouched.
// The worker is best-effort: registration is guarded in site/index.html, and
// the reader works exactly as before when registration is refused.
const CACHE_VERSION = 'jhw-v1';
const FONT_URL = 'fonts/handwriting.woff2';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.add(FONT_URL)).then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key !== CACHE_VERSION).map((key) => caches.delete(key)),
    )).then(() => self.clients.claim()),
  );
});

function isFont(request) {
  return new URL(request.url).pathname.endsWith('/' + FONT_URL);
}

function isScan(request) {
  return new URL(request.url).pathname.includes('/img/');
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (isFont(request)) {
    event.respondWith(
      caches.match(request).then((hit) => hit || fetch(request).then((res) => {
        if (res.ok) caches.open(CACHE_VERSION).then((cache) => cache.put(request, res.clone()));
        return res;
      })),
    );
    return;
  }
  if (isScan(request)) {
    event.respondWith(
      caches.match(request).then((hit) => {
        const network = fetch(request).then((res) => {
          if (res.ok) caches.open(CACHE_VERSION).then((cache) => cache.put(request, res.clone()));
          return res;
        }).catch(() => undefined);
        return hit || network;
      }),
    );
    return;
  }
  // Everything else: network-first, never cached here.
});
