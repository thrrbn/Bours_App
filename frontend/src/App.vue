<script setup>
// Coquille applicative : navigation + bandeau de disclaimer permanent.
// Le disclaimer n'est jamais masquable (docs/17-limites-legales-techniques.md,
// section "Ce qui doit systematiquement apparaitre dans l'interface").
import { RouterLink, RouterView } from "vue-router";
import { useMaintenanceStore } from "./stores/maintenance";

const maintenance = useMaintenanceStore();
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <header class="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <h1 class="text-lg font-semibold">Bourse Assistant</h1>
      <nav class="flex items-center gap-4 text-sm">
        <RouterLink to="/" class="hover:underline">Recherche</RouterLink>
        <RouterLink to="/watchlist" class="hover:underline">Ma watchlist</RouterLink>
        <RouterLink to="/portfolio" class="hover:underline">Portefeuille virtuel</RouterLink>
        <RouterLink to="/top-buys" class="hover:underline">Top achats</RouterLink>
        <RouterLink to="/history" class="hover:underline">Historique des signaux</RouterLink>
        <button
          class="text-xs border rounded px-2 py-1 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
          :disabled="maintenance.isRefreshing"
          @click="maintenance.refreshAll"
        >
          {{ maintenance.isRefreshing ? "Rafraichissement..." : "Tout rafraichir maintenant" }}
        </button>
      </nav>
    </header>

    <div class="bg-amber-50 border-b border-amber-200 text-amber-900 text-xs px-6 py-2">
      Cette application fournit des scores statistiques et des scenarios probables a titre informatif.
      Ce n'est ni un conseil en investissement, ni une garantie de performance future.
    </div>

    <div v-if="maintenance.error" class="bg-red-50 border-b border-red-200 text-red-700 text-xs px-6 py-2">
      {{ maintenance.error }}
    </div>
    <div v-else-if="maintenance.lastSummary" class="bg-emerald-50 border-b border-emerald-200 text-emerald-800 text-xs px-6 py-2">
      Prix : {{ maintenance.lastSummary.prices.total_assets }} actif(s), {{ maintenance.lastSummary.prices.errors }} erreur(s)
      - News : {{ maintenance.lastSummary.news.new_articles }} nouveaux articles
      - Signaux recalcules - Analystes : {{ maintenance.lastSummary.analyst.covered }}/{{ maintenance.lastSummary.analyst.total_assets }} couverts.
    </div>

    <main class="flex-1 px-6 py-6">
      <RouterView />
    </main>
  </div>
</template>
