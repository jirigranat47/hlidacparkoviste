const CACHE_NAME = 'parkoviste-v{{ version }}';
const ASSETS_TO_CACHE = [
    '/',
    '/static/style.css?v={{ version }}',
    '/static/app.js?v={{ version }}',
    '/static/statistics.js?v={{ version }}',
    '/static/history.js?v={{ version }}',
    '/static/favicon.svg',
    '/static/manifest.json',
    '/static/og-image.png'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            // Force reload of these assets from network to ensure freshness
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
    // Force the waiting service worker to become the active service worker
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    // Ensure the service worker takes control of all clients immediately
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
    // Network first strategy for the root HTML to ensure fresh data/token
    // Cache first for static assets

    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => {
                return caches.match(event.request);
            })
        );
        return;
    }

    event.respondWith(
        caches.match(event.request).then((response) => {
            // Return cached response if found, else fetch from network
            return response || fetch(event.request);
        })
    );
});
