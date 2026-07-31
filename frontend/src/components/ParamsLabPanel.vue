<script setup>
// Panneau interactif du "laboratoire de parametres" (31/07/2026, voir
// docs/STACK.md, backend/app/domains/backtests/kernc_engine.py +
// schemas.py::SmaParamsOverride/DecisionParamsOverride). Ouvert depuis une
// position du portefeuille virtuel : permet de rejouer un backtest
// (POST /run-kernc) en modifiant soi-meme les fenetres SMA et les seuils de
// decision, SANS jamais toucher au moteur de signal reel ni au portefeuille
// (ad-hoc, rien n'est sauvegarde - chaque clic sur "Lancer le test" cree un
// nouveau run de backtest independant, consultable via son propre run_id).
import { computed, reactive, ref } from "vue";
import apiClient from "../api/client";

const props = defineProps({
  assetId: { type: String, required: true },
});

// Defauts strictement identiques au comportement de production (voir
// SmaParamsOverride/DecisionParamsOverride cote backend) - modifier ces
// champs ne change RIEN tant qu'on ne clique pas sur "Lancer le test", et
// meme alors, seulement ce run de backtest.
function defaultPeriodStart() {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().slice(0, 10);
}
function defaultPeriodEnd() {
  return new Date().toISOString().slice(0, 10);
}

const periodStart = ref(defaultPeriodStart());
const periodEnd = ref(defaultPeriodEnd());

const smaParams = reactive({ n1: 10, n2: 20 });
const decisionParams = reactive({
  technical_weight: 0.5,
  news_weight: 0.5,
  buy_threshold: 70,
  watch_threshold: 55,
  caution_threshold: 45,
  sell_threshold: 30,
  buy_max_risk: 50,
  sell_min_risk: 60,
  min_confidence: 30,
});
const showAdvanced = ref(false);

const isRunning = ref(false);
const error = ref(null);
const results = ref(null);

const groupedResults = computed(() => {
  if (!results.value) return [];
  return [...results.value].sort((a, b) => {
    if (a.strategy_name !== b.strategy_name) return (a.strategy_name || "").localeCompare(b.strategy_name || "");
    return (a.horizon || "").localeCompare(b.horizon || "");
  });
});

function strategyLabel(name) {
  if (name === "signal_replay") return "Nos signaux (signal_replay)";
  if (name === "sma_cross") return "Croisement SMA (benchmark)";
  if (name === "buy_and_hold") return "Buy & hold (benchmark)";
  return name || "n/d";
}

function fmt(value, digits = 2) {
  return value === null || value === undefined ? "n/d" : Number(value).toFixed(digits);
}

function fmtPct(value, digits = 2) {
  return value === null || value === undefined ? "n/d" : `${Number(value).toFixed(digits)}%`;
}

function extraMetric(row, key) {
  return row.extra_metrics && row.extra_metrics[key] !== undefined ? row.extra_metrics[key] : null;
}

async function runTest() {
  isRunning.value = true;
  error.value = null;
  results.value = null;
  try {
    const { data: runData } = await apiClient.post("/backtests/run-kernc", {
      period_start: periodStart.value,
      period_end: periodEnd.value,
      asset_ids: [props.assetId],
      sma_params: { n1: Number(smaParams.n1), n2: Number(smaParams.n2) },
      decision_params: {
        technical_weight: Number(decisionParams.technical_weight),
        news_weight: Number(decisionParams.news_weight),
        buy_threshold: Number(decisionParams.buy_threshold),
        watch_threshold: Number(decisionParams.watch_threshold),
        caution_threshold: Number(decisionParams.caution_threshold),
        sell_threshold: Number(decisionParams.sell_threshold),
        buy_max_risk: Number(decisionParams.buy_max_risk),
        sell_min_risk: Number(decisionParams.sell_min_risk),
        min_confidence: Number(decisionParams.min_confidence),
      },
    });
    const { data: resultData } = await apiClient.get(`/backtests/${runData.backtest_run_id}`);
    results.value = resultData;
  } catch (err) {
    error.value = "Impossible de lancer ce test (historique de prix/signaux insuffisant sur la periode choisie ?).";
  } finally {
    isRunning.value = false;
  }
}

function resetToDefaults() {
  smaParams.n1 = 10;
  smaParams.n2 = 20;
  decisionParams.technical_weight = 0.5;
  decisionParams.news_weight = 0.5;
  decisionParams.buy_threshold = 70;
  decisionParams.watch_threshold = 55;
  decisionParams.caution_threshold = 45;
  decisionParams.sell_threshold = 30;
  decisionParams.buy_max_risk = 50;
  decisionParams.sell_min_risk = 60;
  decisionParams.min_confidence = 30;
}
</script>

<template>
  <div class="border rounded-lg p-4 bg-gray-50">
    <p class="text-xs text-gray-500 mb-3">
      Rejoue un backtest sur cet actif en changeant les fenetres de moyennes mobiles et les seuils de decision -
      n'affecte jamais le signal reel ni tes positions. Chaque test cree un nouveau run independant.
    </p>

    <div class="grid grid-cols-2 gap-3 mb-3">
      <div>
        <label class="text-xs text-gray-500 block mb-1">Debut de periode</label>
        <input v-model="periodStart" type="date" class="border rounded px-2 py-1 text-sm w-full" />
      </div>
      <div>
        <label class="text-xs text-gray-500 block mb-1">Fin de periode</label>
        <input v-model="periodEnd" type="date" class="border rounded px-2 py-1 text-sm w-full" />
      </div>
    </div>

    <div class="mb-3">
      <p class="text-xs font-semibold text-gray-600 mb-1">Fenetres SMA (strategie croisement, benchmark)</p>
      <div class="flex gap-3">
        <label class="text-xs text-gray-500 flex items-center gap-1">
          n1 (courte)
          <input v-model="smaParams.n1" type="number" min="1" class="border rounded px-2 py-1 text-sm w-20" />
        </label>
        <label class="text-xs text-gray-500 flex items-center gap-1">
          n2 (longue)
          <input v-model="smaParams.n2" type="number" min="1" class="border rounded px-2 py-1 text-sm w-20" />
        </label>
      </div>
    </div>

    <button class="text-xs text-gray-600 hover:underline mb-2" @click="showAdvanced = !showAdvanced">
      {{ showAdvanced ? "▾" : "▸" }} Seuils de decision (strategie "nos signaux") - defauts identiques au moteur reel
    </button>
    <div v-if="showAdvanced" class="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-3 bg-white border rounded p-3">
      <label class="text-xs text-gray-500">
        Poids technique
        <input v-model="decisionParams.technical_weight" type="number" step="0.05" min="0" max="1" class="border rounded px-2 py-1 text-sm w-full" />
      </label>
      <label class="text-xs text-gray-500">
        Poids news
        <input v-model="decisionParams.news_weight" type="number" step="0.05" min="0" max="1" class="border rounded px-2 py-1 text-sm w-full" />
      </label>
      <label class="text-xs text-gray-500">
        Confiance min.
        <input v-model="decisionParams.min_confidence" type="number" step="1" class="border rounded px-2 py-1 text-sm w-full" />
      </label>
      <label class="text-xs text-gray-500">
        Seuil achat
        <input v-model="decisionParams.buy_threshold" type="number" step="1" class="border rounded px-2 py-1 text-sm w-full" />
      </label>
      <label class="text-xs text-gray-500">
        Seuil surveillance
        <input v-model="decisionParams.watch_threshold" type="number" step="1" class="border rounded px-2 py-1 text-sm w-full" />
      </label>
      <label class="text-xs text-gray-500">
        Seuil prudence
        <input v-model="decisionParams.caution_threshold" type="number" step="1" class="border rounded px-2 py-1 text-sm w-full" />
      </label>
      <label class="text-xs text-gray-500">
        Seuil vente
        <input v-model="decisionParams.sell_threshold" type="number" step="1" class="border rounded px-2 py-1 text-sm w-full" />
      </label>
      <label class="text-xs text-gray-500">
        Risque max (achat)
        <input v-model="decisionParams.buy_max_risk" type="number" step="1" class="border rounded px-2 py-1 text-sm w-full" />
      </label>
      <label class="text-xs text-gray-500">
        Risque min (vente)
        <input v-model="decisionParams.sell_min_risk" type="number" step="1" class="border rounded px-2 py-1 text-sm w-full" />
      </label>
    </div>

    <div class="flex gap-2 mb-3">
      <button
        class="px-3 py-1.5 bg-gray-900 text-white rounded text-xs disabled:opacity-40"
        :disabled="isRunning"
        @click="runTest"
      >
        {{ isRunning ? "Test en cours..." : "Lancer le test" }}
      </button>
      <button class="px-3 py-1.5 border rounded text-xs text-gray-600 hover:bg-gray-100" @click="resetToDefaults">
        Reinitialiser les parametres
      </button>
    </div>

    <p v-if="error" class="text-xs text-red-600 mb-3">{{ error }}</p>

    <div v-if="groupedResults.length" class="border rounded bg-white overflow-x-auto">
      <table class="w-full text-xs">
        <thead class="bg-gray-50 text-gray-500 uppercase">
          <tr>
            <th class="text-left px-2 py-1.5">Strategie</th>
            <th class="text-left px-2 py-1.5">Horizon</th>
            <th class="text-right px-2 py-1.5">Precision</th>
            <th class="text-right px-2 py-1.5">Win rate</th>
            <th class="text-right px-2 py-1.5">Sharpe</th>
            <th class="text-right px-2 py-1.5">Sortino</th>
            <th class="text-right px-2 py-1.5">Calmar</th>
            <th class="text-right px-2 py-1.5">Rendement</th>
            <th class="text-right px-2 py-1.5">Drawdown max</th>
          </tr>
        </thead>
        <tbody class="divide-y">
          <tr v-for="row in groupedResults" :key="`${row.strategy_name}-${row.horizon}`">
            <td class="px-2 py-1.5">{{ strategyLabel(row.strategy_name) }}</td>
            <td class="px-2 py-1.5">{{ row.horizon }}</td>
            <td class="px-2 py-1.5 text-right">{{ row.precision !== null ? fmtPct(row.precision * 100) : "n/d" }}</td>
            <td class="px-2 py-1.5 text-right">{{ row.win_rate !== null ? fmtPct(row.win_rate * 100) : "n/d" }}</td>
            <td class="px-2 py-1.5 text-right">{{ fmt(row.sharpe_ratio) }}</td>
            <td class="px-2 py-1.5 text-right">{{ fmt(extraMetric(row, "Sortino Ratio")) }}</td>
            <td class="px-2 py-1.5 text-right">{{ fmt(row.calmar_ratio) }}</td>
            <td class="px-2 py-1.5 text-right">{{ fmtPct(extraMetric(row, "Return [%]")) }}</td>
            <td class="px-2 py-1.5 text-right">{{ fmtPct(row.max_drawdown !== null ? row.max_drawdown * 100 : null) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="results && !groupedResults.length" class="text-xs text-gray-400">
      Aucun resultat - historique de prix/signaux insuffisant sur cette periode pour cet actif.
    </p>
  </div>
</template>
