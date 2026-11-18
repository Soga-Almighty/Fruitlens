/* Fruit Lens service worker.
 *
 * Aturan penting: data pribadi TIDAK PERNAH di-cache.
 *   - /api/*, /uploads/*, /auth/*, "/" dan "/login" selalu lewat jaringan (halaman "/" berbeda isi
 *     tergantung login atau tidak).
 *   - Yang di-cache hanya: ikon, manifest, halaman offline, dan library CDN (tailwind, lucide, chart.js, font).
 * Naikkan VERSION setiap mengubah file ini atau aset statis supaya cache lama dibuang.
 */
const VERSION = "v3";
const STATIC_CACHE = `fruitlens-static-${VERSION}`;
const CDN_CACHE = `fruitlens-cdn-${VERSION}`;

const PRECACHE = [
  "/offline.html",
  "/static/i18n.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch-icon.png",
];

const CDN_HOSTS = ["cdn.tailwindcss.com", "unpkg.com", "cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com"];

self.addEventListener("install", (event) => {
  // Satu per satu: kalau ada satu file yang gagal diambil, instalasi tidak ikut gagal.
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((c) => Promise.all(PRECACHE.map((u) => c.add(u).catch(() => null))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => ![STATIC_CACHE, CDN_CACHE].includes(k)).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Halaman (navigasi): selalu dari jaringan; kalau offline tampilkan halaman offline.
  if (req.mode === "navigate") {
    event.respondWith(fetch(req).catch(() => caches.match("/offline.html")));
    return;
  }

  // Aset statis kita sendiri: cache dulu, perbarui di belakang layar.
  if (url.origin === self.location.origin && url.pathname.startsWith("/static/")) {
    event.respondWith(staleWhileRevalidate(req, STATIC_CACHE));
    return;
  }

  // Library CDN: cache dulu, perbarui di belakang layar.
  if (CDN_HOSTS.includes(url.hostname)) {
    event.respondWith(staleWhileRevalidate(req, CDN_CACHE));
    return;
  }
  // Selain itu (api, uploads, auth, dll.) tidak disentuh: langsung ke jaringan.
});

function staleWhileRevalidate(req, cacheName) {
  return caches.open(cacheName).then((cache) =>
    cache.match(req).then((hit) => {
      const network = fetch(req)
        .then((res) => {
          if (res && (res.ok || res.type === "opaque")) cache.put(req, res.clone());
          return res;
        })
        .catch(() => hit);
      return hit || network;
    }),
  );
}
