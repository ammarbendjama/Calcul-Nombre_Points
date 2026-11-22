/* Service worker : cache du coquillon de l'application (PWA installable). */
const CACHE = "points-copie-v1";
const FICHIERS = ["./index.html", "./app.js", "./manifest.webmanifest",
                  "./icone-192.png", "./icone-512.png"];

self.addEventListener("install", (evenement) => {
  evenement.waitUntil(caches.open(CACHE).then((c) => c.addAll(FICHIERS)));
  self.skipWaiting();
});

self.addEventListener("activate", (evenement) => {
  evenement.waitUntil(
    caches.keys().then((cles) =>
      Promise.all(cles.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (evenement) => {
  const url = new URL(evenement.request.url);
  if (url.origin !== self.location.origin) return; /* CDN tesseract.js : réseau */
  evenement.respondWith(
    caches.match(evenement.request).then((reponse) =>
      reponse || fetch(evenement.request)
    )
  );
});
