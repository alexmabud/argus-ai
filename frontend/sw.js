const CACHE_NAME = "argus-v1";
const STATIC_ASSETS = [
  "/",
  "/css/app.css",
  "/js/app.js",
  "/js/api.js",
  "/js/auth.js",
  "/js/db.js",
  "/js/sync.js",
  "/manifest.json",
];

// Install — cache static assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate — cleanup old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch — network-first for API, cache-first for assets
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (url.pathname.startsWith("/api/")) {
    // API: network-first
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (request.method === "GET" && response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => {
          if (request.method === "GET") {
            return caches.match(request);
          }
          return new Response(
            JSON.stringify({ detail: "Sem conexão. Tente novamente." }),
            { status: 503, headers: { "Content-Type": "application/json" } }
          );
        })
    );
  } else {
    // Assets: cache-first
    event.respondWith(
      caches
        .match(request)
        .then((cached) => cached || fetch(request))
    );
  }
});

// Background sync
self.addEventListener("sync", (event) => {
  if (event.tag === "argus-sync") {
    event.waitUntil(
      self.clients.matchAll().then((clients) => {
        clients.forEach((client) => client.postMessage({ type: "SYNC_NOW" }));
      })
    );
  }
});
