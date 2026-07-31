<script setup>
import { onMounted, ref, watch } from "vue";
import { useAssetsStore } from "../stores/assets";
import { useSignalsStore } from "../stores/signals";
import { useAnalystStore } from "../stores/analyst";
import { useMarketDataStore } from "../stores/marketData";
import SignalCard from "../components/SignalCard.vue";
import HorizonTabs from "../components/HorizonTabs.vue";
import FundamentalsPanel from "../components/FundamentalsPanel.vue";

const props = defineProps({ assetId: { type: String, required: true } });

const assetsStore = useAssetsStore();
const signalsStore = useSignalsStore();
const analystStore = useAnalystStore();
const marketDataStore = useMarketDataStore();
const activeHorizon = ref("short");
const tab = ref("overview"); // 'overview' | 'fundamentals'

async function loadAll() {
  await assetsStore.loadAsset(props.assetId);
  await signalsStore.loadAllHorizons(props.assetId);
  await analystStore.loadComparison(props.assetId, activeHorizon.value);
  await marketDataStore.loadHistoricalTrend(props.assetId);
}

async function onRefreshConsensus() {
  await analystStore.refreshConsensus(props.assetId);
  await analystStore.loadComparison(props.assetId, activeHorizon.value);
}

onMounted(loadAll);
watch(() => props.assetId, loadAll);
watch(() => props.assetId, () => {
  tab.value = "overview";
});
watch(activeHorizon, (horizon) => analystStore.loadComparison(props.assetId, horizon));

function directionClass(direction) {
  if (direction === "achat") return "bg-emerald-50 text-emerald-700 border-emerald-300";
  if (direction === "vente") return "bg-red-50 text-red-700 border-red-300";
  return "bg-gray-100 text-gray-600 border-gray-300";
}

function pnlClass(value) {
  if (value === null || value === undefined) return "text-gray-400";
  return value >= 0 ? "text-emerald-600" : "text-red-600";
}

function fmtPct(value) {
  if (value === null || value === undefined) return "n/d";
  return (value >= 0 ? "+" : "") + value.toFixed(2) + "%";
}
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <div v-if="assetsStore.selectedAsset" class="mb-4">
      <h2 class="text-xl font-semibold">
        {{ assetsStore.selectedAsset.name }}
        <span class="text-gray-400 font-normal">({{ assetsStore.selectedAsset.ticker }})</span>
      </h2>
      <p class="text-sm text-gray-500">
        {{ assetsStore.selectedAsset.market }} - {{ assetsStore.selectedAsset.sector || "Secteur non renseigne" }}
      </p>
    </div>

    <div class="flex gap-2 border-b border-gray-200 mb-4">
      <button
        class="px-3 py-2 text-sm border-b-2 transition-colors"
        :class="tab === 'overview' ? 'border-gray-900 font-medium' : 'border-transparent text-gray-500 hover:text-gray-800'"
        @click="tab = 'overview'"
      >
        Vue d'ensemble
      </button>
      <button
        class="px-3 py-2 text-sm border-b-2 transition-colors"
        :class="tab === 'fundamentals' ? 'border-gray-900 font-medium' : 'border-transparent text-gray-500 hover:text-gray-800'"
        @click="tab = 'fundamentals'"
      >
        Fiche titre
      </button>
    </div>

    <FundamentalsPanel v-if="tab === 'fundamentals'" :asset-id="assetId" />

    <template v-if="tab === 'overview'">
    <HorizonTabs v-model="activeHorizon" />

    <p v-if="signalsStore.error" class="text-sm text-red-600 mb-4">{{ signalsStore.error }}</p>
    <p v-if="signalsStore.isLoading" class="text-sm text-gray-500">Chargement du signal...</p>

    <SignalCard v-if="signalsStore.signalsByHorizon[activeHorizon]" :signal="signalsStore.signalsByHorizon[activeHorizon]" />

    <div class="border rounded-lg p-4 bg-white mt-4" v-if="marketDataStore.trendsByAssetId[assetId]">
      <h3 class="text-sm font-semibold mb-1">Tendance reelle passee</h3>
      <p class="text-xs text-gray-400 mb-3">
        Rendement reel constate (pas une prediction) - point de comparaison pour l'horizon ~12 mois des analystes
        externes, plus long que nos horizons de prediction (5/20/60 jours).
      </p>
      <div class="grid grid-cols-4 gap-2 text-center text-sm">
        <div>
          <div class="text-gray-500 text-xs mb-1">1 mois</div>
          <div class="font-semibold" :class="pnlClass(marketDataStore.trendsByAssetId[assetId].return_1m)">
            {{ fmtPct(marketDataStore.trendsByAssetId[assetId].return_1m) }}
          </div>
        </div>
        <div>
          <div class="text-gray-500 text-xs mb-1">3 mois</div>
          <div class="font-semibold" :class="pnlClass(marketDataStore.trendsByAssetId[assetId].return_3m)">
            {{ fmtPct(marketDataStore.trendsByAssetId[assetId].return_3m) }}
          </div>
        </div>
        <div>
          <div class="text-gray-500 text-xs mb-1">6 mois</div>
          <div class="font-semibold" :class="pnlClass(marketDataStore.trendsByAssetId[assetId].return_6m)">
            {{ fmtPct(marketDataStore.trendsByAssetId[assetId].return_6m) }}
          </div>
        </div>
        <div>
          <div class="text-gray-500 text-xs mb-1">12 mois</div>
          <div class="font-semibold" :class="pnlClass(marketDataStore.trendsByAssetId[assetId].return_12m)">
            {{ fmtPct(marketDataStore.trendsByAssetId[assetId].return_12m) }}
          </div>
        </div>
      </div>
    </div>

    <div class="border rounded-lg p-4 bg-white mt-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold">Comparaison avec les avis externes</h3>
        <button class="text-xs text-gray-500 hover:underline" @click="onRefreshConsensus">
          Rafraichir le consensus
        </button>
      </div>

      <div v-if="analystStore.comparison">
        <div class="grid grid-cols-3 gap-2 mb-3 text-center text-sm">
          <div>
            <div class="text-gray-500 text-xs mb-1">Moteur de regles</div>
            <span class="px-2 py-1 rounded-full text-xs font-medium border" :class="directionClass(analystStore.comparison.internal_rules_direction)">
              {{ analystStore.comparison.internal_rules_direction }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1">Modele ML</div>
            <span
              v-if="analystStore.comparison.internal_ml_direction"
              class="px-2 py-1 rounded-full text-xs font-medium border"
              :class="directionClass(analystStore.comparison.internal_ml_direction)"
            >
              {{ analystStore.comparison.internal_ml_direction }}
            </span>
            <span v-else class="text-xs text-gray-400">
              {{ analystStore.comparison.internal_ml_status === "en_apprentissage" ? "en apprentissage" : "n/d" }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1">Analystes externes</div>
            <span
              v-if="analystStore.comparison.external_consensus_label"
              class="px-2 py-1 rounded-full text-xs font-medium border"
              :class="directionClass(analystStore.comparison.external_consensus_label)"
            >
              {{ analystStore.comparison.external_consensus_label }}
            </span>
            <span v-else class="text-xs text-gray-400">aucune donnee</span>
          </div>
        </div>

        <p class="text-xs text-gray-400 italic mb-3">{{ analystStore.comparison.note }}</p>

        <div v-if="analystStore.comparison.recent_articles.length">
          <p class="text-xs uppercase text-gray-400 mb-1">Articles recents pouvant expliquer ces avis</p>
          <ul class="space-y-1">
            <li v-for="article in analystStore.comparison.recent_articles" :key="article.id" class="text-sm">
              <a :href="article.url" target="_blank" rel="noopener" class="text-blue-600 hover:underline">{{ article.title }}</a>
              <span v-if="article.sentiment_score !== null" class="text-xs text-gray-400 ml-1">
                (sentiment {{ article.sentiment_score.toFixed(2) }})
              </span>
            </li>
          </ul>
        </div>

        <p class="text-xs text-gray-400 italic mt-3">
          Avis d'analystes externes (Yahoo Finance), pas une recommandation de cette application.
        </p>
      </div>
      <p v-else class="text-sm text-gray-400">Chargement de la comparaison...</p>
    </div>
    </template>
  </div>
</template>
