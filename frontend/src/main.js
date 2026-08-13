import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./style.css";

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount("#app");

// PWA : enregistrement du service worker (voir public/sw.js). Silencieux si
// indisponible - navigateur trop ancien, ou contexte non securise (http://
// hors localhost, cas possible en LAN sur le NAS sans HTTPS) : dans ce cas
// le navigateur refuse simplement l'enregistrement, l'app continue de
// fonctionner normalement sans le cache de l'app shell.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Pas de PWA installable sur cette connexion (http:// non local le
      // plus souvent) - pas bloquant, l'app fonctionne comme un site normal.
    });
  });
}
