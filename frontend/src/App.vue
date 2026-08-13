<script setup>
// Coquille applicative : navigation + bandeau de disclaimer permanent.
// Le disclaimer n'est jamais masquable (docs/17-limites-legales-techniques.md,
// section "Ce qui doit systematiquement apparaitre dans l'interface").
import { onMounted, ref } from "vue";
import { RouterLink, RouterView } from "vue-router";
import { useMaintenanceStore } from "./stores/maintenance";

const maintenance = useMaintenanceStore();

// Menu replie par defaut sous le seuil "md" de Tailwind (768px) - GSM et
// tablettes portrait. Au-dela, la nav horizontale complete reste affichee
// en permanence (comportement desktop inchange).
const menuOpen = ref(false);

// PWA : bandeau "Installer l'application" (13/08/2026, ergonomie mobile).
// Chrome/Edge/Android declenchent "beforeinstallprompt" quand l'app est
// installable (manifest + service worker valides, voir public/manifest.json
// et public/sw.js) - on intercepte l'invite native du navigateur pour
// pouvoir la redeclencher depuis notre propre bouton, plus visible qu'une
// icone discrete dans la barre d'adresse. Safari/iOS ne declenchent jamais
// cet evenement (pas de vraie API d'installation programmatique) - pas de
// bandeau sur iOS, l'utilisateur y installe via Partager > Sur l'ecran
// d'accueil.
const showInstallBanner = ref(false);
let deferredInstallPrompt = null;
const INSTALL_DISMISSED_KEY = "bourse_install_banner_dismissed";

onMounted(() => {
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    if (localStorage.getItem(INSTALL_DISMISSED_KEY) !== "1") {
      showInstallBanner.value = true;
    }
  });
  window.addEventListener("appinstalled", () => {
    showInstallBanner.value = false;
    deferredInstallPrompt = null;
  });
});

async function onInstallClick() {
  if (!deferredInstallPrompt) return;
  deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
  showInstallBanner.value = false;
}

function dismissInstallBanner() {
  showInstallBanner.value = false;
  localStorage.setItem(INSTALL_DISMISSED_KEY, "1");
}
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <header class="bg-white border-b border-gray-200 px-4 sm:px-6 py-3">
      <div class="flex items-center justify-between gap-3">
        <RouterLink to="/" class="text-lg font-semibold hover:underline">Bourse Assistant</RouterLink>

        <!-- Nav desktop : inchangee, simplement masquee sous "md". -->
        <nav class="hidden md:flex items-center gap-4 text-sm flex-wrap">
          <RouterLink to="/" class="hover:underline">Marche</RouterLink>
          <RouterLink to="/recherche" class="hover:underline">Recherche</RouterLink>
          <RouterLink to="/watchlist" class="hover:underline">Ma watchlist</RouterLink>
          <RouterLink to="/portfolio" class="hover:underline">Portefeuille virtuel</RouterLink>
          <RouterLink to="/top-buys" class="hover:underline">Top achats</RouterLink>
          <RouterLink to="/status" class="hover:underline">Suivi des actifs</RouterLink>
          <RouterLink to="/history" class="hover:underline">Historique des signaux</RouterLink>
          <RouterLink to="/fiabilite" class="hover:underline">Fiabilite</RouterLink>
          <RouterLink to="/analysis-lab" class="hover:underline">Laboratoire d'analyse</RouterLink>
          <RouterLink to="/briefing" class="hover:underline">Briefing</RouterLink>
          <button
            class="text-xs border rounded px-2 py-1 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
            :disabled="maintenance.isRefreshing"
            @click="maintenance.refreshAll"
          >
            {{ maintenance.isRefreshing ? "Rafraichissement..." : "Tout rafraichir maintenant" }}
          </button>
        </nav>

        <!-- Bouton hamburger : uniquement sous "md". -->
        <button
          class="md:hidden border rounded px-3 py-1.5 text-sm text-gray-600"
          :aria-expanded="menuOpen"
          aria-label="Ouvrir le menu"
          @click="menuOpen = !menuOpen"
        >
          {{ menuOpen ? "Fermer" : "Menu" }}
        </button>
      </div>

      <!-- Nav mobile : liens empiles, repliee/depliee via le bouton ci-dessus. -->
      <nav v-if="menuOpen" class="md:hidden flex flex-col gap-1 text-sm mt-3 pb-1">
        <RouterLink to="/" class="py-1.5 hover:underline" @click="menuOpen = false">Marche</RouterLink>
        <RouterLink to="/recherche" class="py-1.5 hover:underline" @click="menuOpen = false">Recherche</RouterLink>
        <RouterLink to="/watchlist" class="py-1.5 hover:underline" @click="menuOpen = false">Ma watchlist</RouterLink>
        <RouterLink to="/portfolio" class="py-1.5 hover:underline" @click="menuOpen = false">Portefeuille virtuel</RouterLink>
        <RouterLink to="/top-buys" class="py-1.5 hover:underline" @click="menuOpen = false">Top achats</RouterLink>
        <RouterLink to="/status" class="py-1.5 hover:underline" @click="menuOpen = false">Suivi des actifs</RouterLink>
        <RouterLink to="/history" class="py-1.5 hover:underline" @click="menuOpen = false">Historique des signaux</RouterLink>
        <RouterLink to="/fiabilite" class="py-1.5 hover:underline" @click="menuOpen = false">Fiabilite</RouterLink>
        <RouterLink to="/analysis-lab" class="py-1.5 hover:underline" @click="menuOpen = false">Laboratoire d'analyse</RouterLink>
        <RouterLink to="/briefing" class="py-1.5 hover:underline" @click="menuOpen = false">Briefing</RouterLink>
        <button
          class="mt-1 text-xs border rounded px-2 py-1.5 text-gray-600 hover:bg-gray-50 disabled:opacity-40 self-start"
          :disabled="maintenance.isRefreshing"
          @click="maintenance.refreshAll"
        >
          {{ maintenance.isRefreshing ? "Rafraichissement..." : "Tout rafraichir maintenant" }}
        </button>
      </nav>
    </header>

    <div
      v-if="showInstallBanner"
      class="bg-slate-900 text-white text-xs px-4 sm:px-6 py-2 flex items-center justify-between gap-3"
    >
      <span>Installer Bourse Assistant sur cet appareil pour un acces plus rapide, comme une application.</span>
      <div class="flex items-center gap-2 shrink-0">
        <button class="border border-white/40 rounded px-2 py-1 hover:bg-white/10" @click="onInstallClick">
          Installer
        </button>
        <button class="text-white/60 hover:text-white" aria-label="Fermer" @click="dismissInstallBanner">✕</button>
      </div>
    </div>

    <div class="bg-amber-50 border-b border-amber-200 text-amber-900 text-xs px-4 sm:px-6 py-2">
      Cette application fournit des scores statistiques et des scenarios probables a titre informatif.
      Ce n'est ni un conseil en investissement, ni une garantie de performance future.
    </div>

    <div v-if="maintenance.error" class="bg-red-50 border-b border-red-200 text-red-700 text-xs px-4 sm:px-6 py-2">
      {{ maintenance.error }}
    </div>
    <div v-else-if="maintenance.lastSummary" class="bg-emerald-50 border-b border-emerald-200 text-emerald-800 text-xs px-4 sm:px-6 py-2">
      Prix : {{ maintenance.lastSummary.prices.total_assets }} actif(s), {{ maintenance.lastSummary.prices.errors }} erreur(s)
      - News : {{ maintenance.lastSummary.news.new_articles }} nouveaux articles
      - Signaux recalcules - Analystes : {{ maintenance.lastSummary.analyst.covered }}/{{ maintenance.lastSummary.analyst.total_assets }} couverts.
    </div>

    <main class="flex-1 px-4 sm:px-6 py-6 overflow-x-hidden">
      <RouterView />
    </main>
  </div>
</template>
