const CACHE_NAME = 'sulong-nir-v1';
const STATIC_CACHE = 'sulong-nir-static-v1';
const DYNAMIC_CACHE = 'sulong-nir-dynamic-v1';
const OFFLINE_FORM_CACHE = 'sulong-nir-offline-forms-v1';

const STATIC_ASSETS = [
  '/',
  '/static/css/tabler.css',
  '/static/css/tabler-themes.css',
  '/static/js/tabler.min.js',
  '/static/pwa/manifest.json',
];

const OFFLINE_PAGES = [
  '/reports/new/',
  '/reports/',
];

// Install event - cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== STATIC_CACHE && key !== DYNAMIC_CACHE && key !== OFFLINE_FORM_CACHE)
          .map(key => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - network first for API, cache first for static
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests
  if (url.origin !== location.origin) {
    return;
  }

  // API requests - network first, fallback to cache
  if (url.pathname.startsWith('/api/') || url.pathname.includes('/api/')) {
    event.respondWith(networkFirstStrategy(event.request));
    return;
  }

  // Report form pages - cache first for offline access
  if (OFFLINE_PAGES.some(page => url.pathname.startsWith(page))) {
    event.respondWith(cacheFirstStrategy(event.request, OFFLINE_FORM_CACHE));
    return;
  }

  // Static assets - cache first
  if (url.pathname.startsWith('/static/') || url.pathname.endsWith('.css') || url.pathname.endsWith('.js') || url.pathname.endsWith('.png') || url.pathname.endsWith('.ico')) {
    event.respondWith(cacheFirstStrategy(event.request, STATIC_CACHE));
    return;
  }

  // HTML pages - network first, fallback to cache
  if (event.request.headers.get('accept').includes('text/html')) {
    event.respondWith(networkFirstStrategy(event.request, DYNAMIC_CACHE));
    return;
  }

  // Default - network first
  event.respondWith(networkFirstStrategy(event.request));
});

// Network first strategy
async function networkFirstStrategy(request, cacheName = DYNAMIC_CACHE) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    // Return offline page for HTML requests
    if (request.headers.get('accept').includes('text/html')) {
      return caches.match('/') || new Response('Offline', { status: 503 });
    }
    throw error;
  }
}

// Cache first strategy
async function cacheFirstStrategy(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) {
    // Update cache in background
    fetch(request).then(response => {
      if (response.ok) {
        caches.open(cacheName).then(cache => cache.put(request, response));
      }
    }).catch(() => {});
    return cached;
  }

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    // Return offline fallback for HTML
    if (request.headers.get('accept').includes('text/html')) {
      return caches.match('/') || new Response('Offline', { status: 503 });
    }
    throw error;
  }
}

// Background sync for offline form submissions
self.addEventListener('sync', event => {
  if (event.tag === 'sync-reports') {
    event.waitUntil(syncReports());
  }
});

async function syncReports() {
  const db = await openOfflineDB();
  const tx = db.transaction('pendingReports', 'readonly');
  const store = tx.objectStore('pendingReports');
  const reports = await store.getAll();

  for (const report of reports) {
    try {
      const response = await fetch('/reports/new/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(report.data),
      });

      if (response.ok) {
        // Remove from offline storage
        const deleteTx = db.transaction('pendingReports', 'readwrite');
        await deleteTx.objectStore('pendingReports').delete(report.id);
      }
    } catch (error) {
      console.error('Failed to sync report:', error);
    }
  }
}

function openOfflineDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('SulongNIROffline', 1);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = event => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('pendingReports')) {
        db.createObjectStore('pendingReports', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

function getCsrfToken() {
  // In a real implementation, this would get the CSRF token from a cookie or meta tag
  return '';
}

// Handle offline form submission
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'STORE_OFFLINE_REPORT') {
    storeOfflineReport(event.data.report);
  }
});

async function storeOfflineReport(report) {
  const db = await openOfflineDB();
  const tx = db.transaction('pendingReports', 'readwrite');
  await tx.objectStore('pendingReports').add({
    data: report,
    timestamp: Date.now(),
  });

  // Register background sync
  if ('serviceWorker' in navigator && 'sync' in self.registration) {
    self.registration.sync.register('sync-reports');
  }
}

// Periodic background sync for checking updates
self.addEventListener('periodicsync', event => {
  if (event.tag === 'check-updates') {
    event.waitUntil(checkForUpdates());
  }
});

async function checkForUpdates() {
  // Check for new alerts, transit updates, etc.
  console.log('Checking for updates...');
}