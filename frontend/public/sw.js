/**
 * Service worker PWA - Bourse Assistant.
 *
 * 13/08/2026 : demande explicite "ameliorer l'ergonomie mobile en gardant
 * les outils connus" -> PWA plutot que Capacitor/refonte native, pour
 * rester sur la stack Vue/Vite existante (voir docs/17 pour le contexte
 * mono-utilisateur, donnees rafraichies manuellement/3x jour).
 *
 * Regle centrale : ne JAMAIS mettre en cache les reponses de /api/ - ce
 * sont des donnees de marche/portefeuille qui doivent toujours refleter
 * l'etat reel du backend, jamais une version perimee servie hors-ligne.
 * Seul l'app shell (JS/CSS/HTML/icones) est mis en cache, pour un
 * chargement rapide et une tolerance aux coupures reseau breves - pas pour
 * un vrai mode hors-ligne complet (pas pertinent pour une app de donnees
 * de marche en temps quasi-reel).
 */

const CACHE_VERSION = "bourse-shell-v1";
const APP_SHELL = ["/", "/manifest.json", "/icon-192.png", "/icon-512.png", "/apple-touch-icon.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(APP_SHELL)).catch(() => {
      // Best-effort : un echec de pre-cache (ex. offline au premier install)
      // ne doit pas empecher l'installation du service worker lui-meme.
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Jamais l'API : toujours reseau, jamais de reponse mise en cache servie
  // a la place (donnees de marche/portefeuille = toujours fraiches).
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // App shell : "stale-while-revalidate" - reponse immediate depuis le
  // cache si disponible (affichage instantane, utile en 3G/4G faible sur
  // mobile), puis mise a jour silencieuse du cache en arriere-plan pour la
  // prochaine visite.
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response && response.ok && response.type === "basic") {
            const clone = response.clone();
            caches.open(CACHE_VERSION).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
