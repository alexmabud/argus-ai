const CACHE_NAME = "argus-v9";
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

// Fetch — só intercepta requisições same-origin.
// Requisições cross-origin (MinIO, OSM tiles, CDNs) são tratadas diretamente
// pelo browser — a SW não interfere para evitar respostas opacas em <img>.
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Deixa o browser tratar recursos de outras origens diretamente
  if (url.origin !== self.location.origin) {
    return;
  }

  if (url.pathname.startsWith("/api/")) {
    // API: network-first
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (request.method === "GET" && response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone)).catch(() => {});
          }
          return response;
        })
        .catch(() => {
          if (request.method === "GET") {
            return caches.match(request).then(
              (cached) =>
                cached ||
                new Response(
                  JSON.stringify({ detail: "Sem conexão. Tente novamente." }),
                  { status: 503, headers: { "Content-Type": "application/json" } }
                )
            );
          }
          return new Response(
            JSON.stringify({ detail: "Sem conexão. Tente novamente." }),
            { status: 503, headers: { "Content-Type": "application/json" } }
          );
        })
    );
  } else {
    // Assets: network-first, fallback to cache
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone)).catch(() => {});
          }
          return response;
        })
        .catch(() =>
          caches
            .match(request)
            .then((cached) => cached || new Response("", { status: 503 }))
        )
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
