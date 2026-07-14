const CACHE_NAME = 'argus-BUILD_HASH';
const STATIC_ASSETS = [
  "/",
  "/css/app.css",
  "/js/app.js",
  "/js/api.js",
  "/js/auth.js",
  "/js/db.js",
  "/js/sync.js",
  "/manifest.json",
  // Libs self-hosted — precache para offline-first (G3-1).
  "/vendor/alpine.min.js",
  "/vendor/apexcharts.min.js",
  "/vendor/qrcode.min.js",
  "/vendor/dexie.min.js",
  "/vendor/leaflet.js",
  "/vendor/leaflet.css",
  "/vendor/leaflet.markercluster.js",
  "/vendor/MarkerCluster.css",
  "/vendor/MarkerCluster.Default.css",
  "/vendor/leaflet-heat.js",
  "/vendor/images/marker-icon.png",
  "/vendor/images/marker-icon-2x.png",
  "/vendor/images/marker-shadow.png",
  "/vendor/images/layers.png",
  "/vendor/images/layers-2x.png",
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
    // API: network-only. Respostas de /api/ nunca entram em Cache Storage
    // (achado #11/2026-07-13) — a maioria carrega PII (pessoas, abordagens,
    // fotos, ocorrências), e o Cache Storage não é limpo por sessão: um
    // dispositivo compartilhado que troca de operador podia servir dados
    // cacheados da sessão anterior enquanto offline. O caminho de dados
    // offline-first de verdade é o IndexedDB (cifrado, ver db.js), não o
    // Cache Storage — não há perda de funcionalidade offline aqui.
    event.respondWith(
      fetch(request).catch(
        () =>
          new Response(
            JSON.stringify({ detail: "Sem conexão. Tente novamente." }),
            { status: 503, headers: { "Content-Type": "application/json" } }
          )
      )
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
            .catch(() => new Response("", { status: 503 }))
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
