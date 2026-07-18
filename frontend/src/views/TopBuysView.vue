<script setup>
// Hit parade + tableau de comparaison (Etape 15 etendue) : pour chaque actif,
// on montre cote a cote la proposition externe (analystes Yahoo) et nos
// propres predictions (moteur de regles + modele ML), avec un indicateur
// d'accord/desaccord - le but etant de juger visuellement, au fil du temps,
// laquelle des sources colle le mieux a la realite (voir docs/11).
import { onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useAnalystStore } from "../stores/analyst";
import { useMarketDataStore } from "../stores/marketData";
import HorizonTabs from "../components/HorizonTabs.vue";

const store = useAnalystStore();
const marketDataStore = useMarketDataStore();
const router = useRouter();
const refreshSummary = ref(null);
const activeHorizon = ref("medium");

async function loadTable() {
  await store.loadComparisonTable(activeHorizon.value);
  // Tendance reelle 12 mois par actif - point de comparaison honnete face a
  // l'horizon ~12 mois des analystes externes (voir docs/11).
  await Promise.all(store.comparisonTable.map((row) => marketDataStore.loadHistoricalTrend(row.asset.id)));
}

onMounted(loadTable);
watch(activeHorizon, loadTable);

function pnlClass(value) {
  if (value === null || value === undefined) return "text-gray-400";
  return value >= 0 ? "text-emerald-600" : "text-red-600";
}

function fmtPct(value) {
  if (value === null || value === undefined) return "n/d";
  return (value >= 0 ? "+" : "") + value.toFixed(2) + "%";
}

async function onRefreshAll() {
  refreshSummary.value = null;
  const result = await store.refreshAll();
  if (result) {
    refreshSummary.value = result;
    await loadTable();
  }
}

function goToAsset(assetId) {
  router.push({ name: "dashboard", params: { assetId } });
}

function directionClass(direction) {
  if (direction === "achat") return "bg-emerald-50 text-emerald-700 border-emerald-300";
  if (direction === "vente") return "bg-red-50 text-red-700 border-red-300";
  return "bg-gray-100 text-gray-600 border-gray-300";
}

// Barre graphique du score externe : -2 (vente forte) a +2 (achat fort),
// centree, largeur proportionnelle a l'intensite.
function barStyle(score) {
  if (score === null || score === undefined) return { width: "0%", background: "var(--border, #d1d5db)" };
  const pct = Math.min(Math.abs(score) / 2, 1) * 50;
  const isPositive = score >= 0;
  return {
    width: pct + "%",
    marginLeft: isPositive ? "50%" : 50 - pct + "%",
    background: isPositive ? "#10b981" : "#ef4444",
  };
}
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <div class="flex items-center justify-between mb-1">
      <h2 class="text-xl font-semibold">Top achats et comparaison des predictions</h2>
      <button class="text-xs text-gray-500 hover:underline whitespace-nowrap" @click="onRefreshAll">
        Rafraichir tout
      </button>
    </div>
    <p class="text-xs text-gray-400 mb-3">
      "Externe" = avis d'analystes tiers (Yahoo Finance), pas une recommandation de cette application.
      "Regles"/"ML" = nos propres predictions, pour comparer visuellement laquelle colle le mieux a la realite.
    </p>

    <HorizonTabs v-model="activeHorizon" />

    <p v-if="refreshSummary" class="text-xs text-gray-500 mb-3">
      {{ refreshSummary.covered }}/{{ refreshSummary.total_assets }} actifs couverts par des analystes
      ({{ refreshSummary.errors }} erreur(s)).
    </p>

    <p v-if="store.error" class="text-sm text-red-600 mb-4">{{ store.error }}</p>
    <p v-if="store.isLoading" class="text-sm text-gray-500">Chargement...</p>
    <p v-if="!store.isLoading && !store.comparisonTable.length" class="text-sm text-gray-400">
      Aucune donnee - clique "Rafraichir tout" ci-dessus, ou "Tout rafraichir maintenant" dans l'en-tete.
    </p>

    <div v-if="store.comparisonTable.length" class="border rounded bg-white overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
          <tr>
            <th class="text-left px-3 py-2">Actif</th>
            <th class="text-left px-3 py-2">Externe (Yahoo)</th>
            <th class="text-center px-3 py-2">Regles</th>
            <th class="text-center px-3 py-2">ML</th>
            <th class="text-center px-3 py-2">Accord</th>
            <th class="text-right px-3 py-2">Tendance 12m (reel)</th>
          </tr>
        </thead>
        <tbody class="divide-y">
          <tr v-for="row in store.comparisonTable" :key="row.asset.id" class="hover:bg-gray-50 cursor-pointer" @click="goToAsset(row.asset.id)">
            <td class="px-3 py-2">
              <span class="font-medium">{{ row.asset.ticker }}</span>
              <span class="text-gray-500 text-xs block">{{ row.asset.name }}</span>
            </td>
            <td class="px-3 py-2">
              <div v-if="row.external_consensus_label" class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-xs font-medium border" :class="directionClass(row.external_consensus_label)">
                  {{ row.external_consensus_label }}
                </span>
                <div class="relative h-1.5 w-20 bg-gray-100 rounded-full overflow-hidden">
                  <div class="absolute top-0 h-1.5 rounded-full" :style="barStyle(row.external_consensus_score)"></div>
                </div>
              </div>
              <span v-else class="text-xs text-gray-400">aucune donnee</span>
            </td>
            <td class="px-3 py-2 text-center">
              <span class="px-2 py-0.5 rounded-full text-xs font-medium border" :class="directionClass(row.internal_rules_direction)">
                {{ row.internal_rules_direction }}
              </span>
            </td>
            <td class="px-3 py-2 text-center">
              <span
                v-if="row.internal_ml_direction"
                class="px-2 py-0.5 rounded-full text-xs font-medium border"
                :class="directionClass(row.internal_ml_direction)"
              >
                {{ row.internal_ml_direction }}
              </span>
              <span v-else class="text-xs text-gray-400">
                {{ row.internal_ml_status === "en_apprentissage" ? "apprentissage" : "n/d" }}
              </span>
            </td>
            <td class="px-3 py-2 text-center">
              <span v-if="row.agreement_rules === true" class="text-emerald-600" title="Regles d'accord avec l'externe">R✓</span>
              <span v-else-if="row.agreement_rules === false" class="text-red-500" title="Regles en desaccord avec l'externe">R✗</span>
              <span v-if="row.agreement_ml === true" class="text-emerald-600 ml-1" title="ML d'accord avec l'externe">M✓</span>
              <span v-else-if="row.agreement_ml === false" class="text-red-500 ml-1" title="ML en desaccord avec l'externe">M✗</span>
            </td>
            <td class="px-3 py-2 text-right font-medium" :class="pnlClass(marketDataStore.trendsByAssetId[row.asset.id]?.return_12m)">
              {{ fmtPct(marketDataStore.trendsByAssetId[row.asset.id]?.return_12m) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
