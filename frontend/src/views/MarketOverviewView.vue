<script setup>
// Page "Marche" (01/08/2026, revue le meme jour) : photo du marche du
// moment - indices + plus fortes hausses/baisses, TOUJOURS EN DIRECT depuis
// des sources de reference externes et gratuites (Yahoo Finance, Binance -
// voir backend/app/domains/market_overview/provider.py), jamais limitees
// aux actifs personnellement suivis dans cette application. Chaque ligne
// est cliquable vers la fiche de cotation d'origine. Rafraichie
// automatiquement 3x/jour (7h, 12h, 17h) par un job planifie - cette page ne
// fait que LIRE le dernier instantane au chargement, "Actualiser"
// ci-dessous permet de forcer un nouveau calcul entre deux horaires fixes.
import { computed, onMounted } from "vue";
import { useMarketOverviewStore } from "../stores/marketOverview";

const store = useMarketOverviewStore();

onMounted(() => store.load());

const hasSnapshot = computed(() => !!store.snapshot?.captured_at);

const MOVER_SECTIONS = [
  { key: "FR", label: "France (CAC 40)", referenceUrl: "https://fr.finance.yahoo.com/quote/%5EFCHI", referenceLabel: "Yahoo Finance France" },
  {
    key: "US",
    label: "Etats-Unis",
    referenceUrl: "https://finance.yahoo.com/screener/predefined/day_gainers",
    referenceLabel: "Yahoo Finance US",
  },
  { key: "CRYPTO", label: "Crypto (Binance)", referenceUrl: "https://www.binance.com/en/markets/overview", referenceLabel: "Binance" },
];

function pnlClass(value) {
  if (value === null || value === undefined) return "text-gray-400";
  return value >= 0 ? "text-emerald-600" : "text-red-600";
}

function fmtPct(value) {
  if (value === null || value === undefined) return "n/d";
  return (value >= 0 ? "+" : "") + value.toFixed(2) + "%";
}

function fmtPrice(value, currency) {
  if (value === null || value === undefined) return "n/d";
  // Certaines cryptos valent une fraction de centime (ex. SHIB) - 2
  // decimales fixes les afficherait toutes a "0.00". On adapte la precision
  // a l'ordre de grandeur du prix plutot qu'un nombre fixe de decimales.
  const decimals = Math.abs(value) < 1 ? 6 : 2;
  const formatted = value.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: decimals });
  return currency ? `${formatted} ${currency}` : formatted;
}

function fmtDateTime(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleString("fr-BE", { dateStyle: "medium", timeStyle: "short" });
}
</script>

<template>
  <div class="max-w-5xl mx-auto">
    <div class="flex items-center justify-between gap-3 mb-1 flex-wrap">
      <h2 class="text-xl font-semibold">Marche</h2>
      <button
        class="text-xs border rounded px-3 py-1.5 text-gray-600 hover:bg-gray-50 disabled:opacity-40 whitespace-nowrap"
        :disabled="store.isRefreshing"
        @click="store.refreshNow"
      >
        {{ store.isRefreshing ? "Actualisation..." : "Actualiser" }}
      </button>
    </div>
    <p class="text-xs text-gray-400 mb-1">
      Donnees en direct depuis Yahoo Finance et Binance (references gratuites, pas les actifs suivis dans cette
      application) - mises a jour automatiquement 7h, 12h et 17h. Clique un titre pour voir sa fiche complete sur la
      source d'origine.
    </p>
    <p v-if="hasSnapshot" class="text-xs text-gray-400 mb-4">
      Derniere mise a jour : {{ fmtDateTime(store.snapshot.captured_at) }}
    </p>
    <div v-else class="mb-4"></div>

    <p v-if="store.error" class="text-sm text-red-600 mb-4">{{ store.error }}</p>
    <p v-if="store.isLoading" class="text-sm text-gray-500">Chargement...</p>
    <p v-if="!store.isLoading && !hasSnapshot" class="text-sm text-gray-400">
      Aucun instantane pour l'instant - clique "Actualiser" ci-dessus, ou attends le prochain rafraichissement
      planifie (7h, 12h ou 17h).
    </p>

    <template v-if="hasSnapshot">
      <!-- Indices -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mb-6">
        <a
          v-for="idx in store.snapshot.indices"
          :key="idx.ticker"
          :href="idx.url"
          target="_blank"
          rel="noopener noreferrer"
          class="border rounded-lg p-3 bg-white text-center hover:bg-gray-50"
        >
          <div class="text-xs text-gray-400 mb-0.5">{{ idx.zone }}</div>
          <div class="text-sm font-semibold mb-1">{{ idx.label }}</div>
          <div class="text-sm">{{ fmtPrice(idx.last_price, idx.currency) }}</div>
          <div class="text-xs font-medium" :class="pnlClass(idx.change_pct)">{{ fmtPct(idx.change_pct) }}</div>
        </a>
        <p v-if="!store.snapshot.indices.length" class="col-span-full text-sm text-gray-400">
          Aucun indice disponible pour l'instant.
        </p>
      </div>

      <!-- Mouvements FR / US / Crypto -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="section in MOVER_SECTIONS" :key="section.key">
          <div class="flex items-center justify-between gap-2 mb-2">
            <h3 class="text-sm font-semibold">{{ section.label }}</h3>
            <a
              :href="section.referenceUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="text-xs text-gray-400 hover:underline whitespace-nowrap"
            >
              {{ section.referenceLabel }} ↗
            </a>
          </div>

          <div class="mb-3">
            <div class="text-xs text-gray-500 mb-1">Plus fortes hausses</div>
            <div class="border rounded bg-white overflow-hidden">
              <table class="w-full text-sm">
                <tbody class="divide-y">
                  <tr
                    v-for="row in store.snapshot.movers[section.key]?.gainers ?? []"
                    :key="row.ticker"
                    class="hover:bg-gray-50 cursor-pointer"
                    @click="row.url && window.open(row.url, '_blank', 'noopener,noreferrer')"
                  >
                    <td class="px-3 py-1.5">
                      <span class="font-medium">{{ row.ticker }}</span>
                      <span class="text-gray-500 text-xs block">{{ row.name }}</span>
                    </td>
                    <td class="px-3 py-1.5 text-right">{{ fmtPrice(row.last_price, row.currency) }}</td>
                    <td class="px-3 py-1.5 text-right font-medium" :class="pnlClass(row.change_pct)">
                      {{ fmtPct(row.change_pct) }}
                    </td>
                  </tr>
                  <tr v-if="!(store.snapshot.movers[section.key]?.gainers ?? []).length">
                    <td class="px-3 py-2 text-xs text-gray-400">Aucune donnee.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <div class="text-xs text-gray-500 mb-1">Plus fortes baisses</div>
            <div class="border rounded bg-white overflow-hidden">
              <table class="w-full text-sm">
                <tbody class="divide-y">
                  <tr
                    v-for="row in store.snapshot.movers[section.key]?.losers ?? []"
                    :key="row.ticker"
                    class="hover:bg-gray-50 cursor-pointer"
                    @click="row.url && window.open(row.url, '_blank', 'noopener,noreferrer')"
                  >
                    <td class="px-3 py-1.5">
                      <span class="font-medium">{{ row.ticker }}</span>
                      <span class="text-gray-500 text-xs block">{{ row.name }}</span>
                    </td>
                    <td class="px-3 py-1.5 text-right">{{ fmtPrice(row.last_price, row.currency) }}</td>
                    <td class="px-3 py-1.5 text-right font-medium" :class="pnlClass(row.change_pct)">
                      {{ fmtPct(row.change_pct) }}
                    </td>
                  </tr>
                  <tr v-if="!(store.snapshot.movers[section.key]?.losers ?? []).length">
                    <td class="px-3 py-2 text-xs text-gray-400">Aucune donnee.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
