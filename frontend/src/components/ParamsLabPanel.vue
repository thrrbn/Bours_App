<script setup>
// Panneau interactif du "laboratoire de parametres" (31/07/2026, voir
// docs/STACK.md, backend/app/domains/backtests/kernc_engine.py +
// schemas.py::SmaParamsOverride/DecisionParamsOverride). Ouvert depuis une
// position du portefeuille virtuel : permet de rejouer un backtest
// (POST /run-kernc) en modifiant soi-meme les fenetres SMA et les seuils de
// decision, SANS jamais toucher au moteur de signal reel ni au portefeuille
// (ad-hoc, rien n'est sauvegarde - chaque clic sur "Lancer le test" cree un
// nouveau run de backtest independant, consultable via son propre run_id).
import { computed, onMounted, reactive, ref } from "vue";
import apiClient from "../api/client";
import {
  METRIC_GLOSSARY,
  STRATEGY_GLOSSARY,
  GUIDE_SECTIONS,
  interpretMetric,
  toneClasses,
  buildSynthesis,
  classifyScorecardConfidence,
} from "../constants/backtestingGlossary";
import { useStrategyScorecardStore } from "../stores/strategyScorecard";

// 13/08/2026 : "arbitrer entre strategies plutot que de juger sur un seul
// backtest" - le scorecard hebdomadaire (evalue automatiquement sur tout le
// portefeuille, voir jobs/evaluate_strategies_job.py) est charge ici pour
// donner du contexte a CHAQUE run ponctuel de ce panneau, plutot que de le
// laisser isole dans la page Fiabilite. Un seul chargement partage si
// l'utilisateur a deja visite /fiabilite dans cette session (store Pinia).
const strategyScorecardStore = useStrategyScorecardStore();
onMounted(() => {
  if (!strategyScorecardStore.scorecard && !strategyScorecardStore.isLoading) {
    strategyScorecardStore.load();
  }
});

// Correspondance directe : les runs ad-hoc de ce panneau (POST /run,
// /run-kernc) et le job planifie utilisent exactement les memes couples
// (strategy_name, horizon) - "short"/"medium"/"long" pour internal_rules/
// signal_replay, "n/a" pour les benchmarks independants de l'horizon (voir
// backend/.../backtests/router.py). Retourne null si aucun historique n'a
// encore ete calcule pour cette combinaison precise.
function historicalStats(row) {
  const scorecard = strategyScorecardStore.scorecard;
  if (!scorecard) return null;
  return scorecard.results.find((r) => r.strategy_name === row.strategy_name && r.horizon === row.horizon) || null;
}

function fmtHistWinRate(stats) {
  if (!stats || stats.avg_win_rate === null || stats.avg_win_rate === undefined) return "n/d";
  return `${(stats.avg_win_rate * 100).toFixed(0)}%`;
}

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
// 13/08/2026 : trois strategies benchmark supplementaires (voir
// kernc_engine.py::RsiStrategy/MacdStrategy/BollingerStrategy) - meme
// principe que smaParams, chacune avec ses propres parametres modulables.
const rsiParams = reactive({ period: 14, oversold: 30, overbought: 70 });
const macdParams = reactive({ fast: 12, slow: 26, signal: 9 });
const bollingerParams = reactive({ period: 20, num_std: 2.0 });
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
const showBenchmarks = ref(false);

const isRunning = ref(false);
const error = ref(null);
const results = ref(null);

// Graphique interactif (bt.plot(), voir kernc_engine.py::_render_plot_html) :
// un seul affiche a la fois (chaque graphique pese plusieurs dizaines de Ko
// et embarque du JS Bokeh - eviter d'en charger plusieurs simultanement).
const activePlotKey = ref(null);

function resultKey(row) {
  return `${row.strategy_name}-${row.horizon}`;
}

function togglePlot(row) {
  const key = resultKey(row);
  activePlotKey.value = activePlotKey.value === key ? null : key;
}

// Explications pedagogiques (01/08/2026, voir constants/backtestingGlossary.js) :
// bouton "?" cliquable par metrique (au lieu d'un simple survol - accessible
// aussi au toucher sur mobile/tablette) + guide replie en haut du panneau.
const openInfoKey = ref(null);
function toggleInfo(key) {
  openInfoKey.value = openInfoKey.value === key ? null : key;
}
const showGuide = ref(false);

const groupedResults = computed(() => {
  if (!results.value) return [];
  return [...results.value].sort((a, b) => {
    if (a.strategy_name !== b.strategy_name) return (a.strategy_name || "").localeCompare(b.strategy_name || "");
    return (a.horizon || "").localeCompare(b.horizon || "");
  });
});

const activePlotResult = computed(() => groupedResults.value.find((row) => resultKey(row) === activePlotKey.value));

function strategyLabel(name) {
  if (name === "internal_rules") return "Moteur interne (regles)";
  if (name === "signal_replay") return "Nos signaux (signal_replay)";
  if (name === "sma_cross") return "Croisement SMA (benchmark)";
  if (name === "rsi_mean_reversion") return "RSI (benchmark)";
  if (name === "macd_cross") return "MACD (benchmark)";
  if (name === "bollinger_reversion") return "Bollinger (benchmark)";
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

// Toutes les statistiques renvoyees par backtesting.py (voir
// backend/.../kernc_engine.py::_EXTRA_STATS_KEYS et les champs types du
// resultat) - regroupees par theme, une ligne = une metrique avec son
// explication pedagogique (constants/backtestingGlossary.js). "field" lit un
// champ type du resultat (deja converti/normalise cote backend), "extra" lit
// la cle brute de backtesting.py dans extra_metrics. `scale100` : le champ
// backend est stocke en ratio 0-1 (comme le reste de l'app), affiche en %
// ici pour coller a la convention native de backtesting.py.
const METRIC_GROUPS = [
  {
    title: "Rendement",
    rows: [
      { key: "return_pct", label: "Rendement total", source: "extra", raw: "Return [%]", fmt: "pct" },
      { key: "buy_hold_return_pct", label: "Rendement buy & hold", source: "extra", raw: "Buy & Hold Return [%]", fmt: "pct" },
      { key: "return_ann_pct", label: "Rendement annualise", source: "extra", raw: "Return (Ann.) [%]", fmt: "pct" },
      { key: "cagr_pct", label: "CAGR", source: "extra", raw: "CAGR [%]", fmt: "pct" },
      { key: "equity_final", label: "Capital final", source: "extra", raw: "Equity Final [$]", fmt: "money" },
      { key: "equity_peak", label: "Capital maximum", source: "extra", raw: "Equity Peak [$]", fmt: "money" },
      { key: "commissions", label: "Frais payes", source: "extra", raw: "Commissions [$]", fmt: "money" },
    ],
  },
  {
    title: "Risque",
    rows: [
      { key: "volatility_ann_pct", label: "Volatilite annualisee", source: "extra", raw: "Volatility (Ann.) [%]", fmt: "pct" },
      { key: "exposure_time", label: "Temps d'exposition", source: "extra", raw: "Exposure Time [%]", fmt: "pct" },
      { key: "max_drawdown_pct", label: "Perte maximale (drawdown)", source: "field", raw: "max_drawdown", fmt: "pct", scale100: true, interpret: true },
      { key: "avg_drawdown_pct", label: "Chute moyenne", source: "extra", raw: "Avg. Drawdown [%]", fmt: "pct" },
      { key: "max_drawdown_duration", label: "Duree de la pire chute", source: "extra", raw: "Max. Drawdown Duration", fmt: "days" },
      { key: "avg_drawdown_duration", label: "Duree de recuperation moyenne", source: "extra", raw: "Avg. Drawdown Duration", fmt: "days" },
    ],
  },
  {
    title: "Ratios ajustes au risque",
    rows: [
      { key: "sharpe_ratio", label: "Ratio de Sharpe", source: "field", raw: "sharpe_ratio", fmt: "num", interpret: true },
      { key: "sortino_ratio", label: "Ratio de Sortino", source: "extra", raw: "Sortino Ratio", fmt: "num", interpret: true },
      { key: "calmar_ratio", label: "Ratio de Calmar", source: "field", raw: "calmar_ratio", fmt: "num", interpret: true },
      { key: "alpha_pct", label: "Alpha", source: "extra", raw: "Alpha [%]", fmt: "pct" },
      { key: "beta", label: "Beta", source: "extra", raw: "Beta", fmt: "num" },
    ],
  },
  {
    title: "Transactions",
    rows: [
      { key: "num_trades", label: "Nombre de transactions", source: "field", raw: "signal_count", fmt: "int" },
      { key: "win_rate_pct", label: "Taux de reussite", source: "field", raw: "win_rate", fmt: "pct", scale100: true, interpret: true },
      { key: "best_trade_pct", label: "Meilleure transaction", source: "extra", raw: "Best Trade [%]", fmt: "pct" },
      { key: "worst_trade_pct", label: "Pire transaction", source: "extra", raw: "Worst Trade [%]", fmt: "pct" },
      { key: "avg_trade_pct", label: "Gain moyen par transaction", source: "extra", raw: "Avg. Trade [%]", fmt: "pct" },
      { key: "max_trade_duration", label: "Duree max d'une transaction", source: "extra", raw: "Max. Trade Duration", fmt: "days" },
      { key: "avg_trade_duration", label: "Duree moyenne d'une transaction", source: "extra", raw: "Avg. Trade Duration", fmt: "days" },
      { key: "false_positive_rate_pct", label: "Taux de faux positifs (moteur interne)", source: "field", raw: "false_positive_rate", fmt: "pct", scale100: true },
      { key: "avg_risk_reward", label: "Ratio gain/perte moyen (moteur interne)", source: "field", raw: "avg_risk_reward", fmt: "num" },
    ],
  },
  {
    title: "Robustesse",
    rows: [
      { key: "profit_factor", label: "Facteur de profit", source: "field", raw: "profit_factor", fmt: "num", interpret: true },
      { key: "expectancy_pct", label: "Esperance de gain", source: "extra", raw: "Expectancy [%]", fmt: "pct" },
      { key: "sqn", label: "SQN", source: "extra", raw: "SQN", fmt: "num", interpret: true },
      { key: "kelly_criterion", label: "Critere de Kelly", source: "extra", raw: "Kelly Criterion", fmt: "num" },
    ],
  },
];

function metricValue(row, metric) {
  let value = metric.source === "field" ? row[metric.raw] : extraMetric(row, metric.raw);
  if (value === null || value === undefined) return null;
  value = Number(value);
  if (metric.scale100) value *= 100;
  return value;
}

function formatMetric(row, metric) {
  const value = metricValue(row, metric);
  if (value === null) return "n/d";
  if (metric.fmt === "pct") return fmtPct(value);
  if (metric.fmt === "money")
    return `${Number(value).toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} $`;
  if (metric.fmt === "days") return `${fmt(value, 1)} j`;
  if (metric.fmt === "int") return String(Math.round(value));
  return fmt(value);
}

function metricInterpretation(row, metric) {
  if (!metric.interpret) return null;
  return interpretMetric(metric.key, metricValue(row, metric));
}

async function runTest() {
  isRunning.value = true;
  error.value = null;
  results.value = null;
  activePlotKey.value = null;

  const decisionParamsPayload = {
    technical_weight: Number(decisionParams.technical_weight),
    news_weight: Number(decisionParams.news_weight),
    buy_threshold: Number(decisionParams.buy_threshold),
    watch_threshold: Number(decisionParams.watch_threshold),
    caution_threshold: Number(decisionParams.caution_threshold),
    sell_threshold: Number(decisionParams.sell_threshold),
    buy_max_risk: Number(decisionParams.buy_max_risk),
    sell_min_risk: Number(decisionParams.sell_min_risk),
    min_confidence: Number(decisionParams.min_confidence),
  };

  // 01/08/2026 : deux moteurs lances en parallele avec les MEMES parametres
  // de decision, resultats fusionnes dans le meme tableau comparatif (voir
  // strategyLabel()/STRATEGY_GLOSSARY.internal_rules) - le moteur interne
  // (backend/.../backtests/service.py::run_backtest_for_asset) est desormais
  // paramétrable au meme titre que backtesting.py (kernc_engine.py). Chaque
  // appel est isole dans son propre try/catch : si l'un des deux moteurs
  // echoue (ex. pas assez de signaux pour signal_replay) sur cet actif/
  // periode, on affiche quand meme les resultats de l'autre plutot que de
  // tout faire echouer.
  const merged = [];
  let anySucceeded = false;

  try {
    const { data: runData } = await apiClient.post("/backtests/run-kernc", {
      period_start: periodStart.value,
      period_end: periodEnd.value,
      asset_ids: [props.assetId],
      sma_params: { n1: Number(smaParams.n1), n2: Number(smaParams.n2) },
      rsi_params: {
        period: Number(rsiParams.period),
        oversold: Number(rsiParams.oversold),
        overbought: Number(rsiParams.overbought),
      },
      macd_params: {
        fast: Number(macdParams.fast),
        slow: Number(macdParams.slow),
        signal: Number(macdParams.signal),
      },
      bollinger_params: { period: Number(bollingerParams.period), num_std: Number(bollingerParams.num_std) },
      decision_params: decisionParamsPayload,
    });
    const { data: resultData } = await apiClient.get(`/backtests/${runData.backtest_run_id}`);
    merged.push(...resultData);
    anySucceeded = true;
  } catch (err) {
    // Gere plus bas : erreur globale seulement si les DEUX moteurs echouent.
  }

  try {
    const { data: runData } = await apiClient.post("/backtests/run", {
      engine_version: "rules_v1",
      period_start: periodStart.value,
      period_end: periodEnd.value,
      asset_ids: [props.assetId],
      decision_params: decisionParamsPayload,
    });
    const { data: resultData } = await apiClient.get(`/backtests/${runData.backtest_run_id}`);
    merged.push(...resultData);
    anySucceeded = true;
  } catch (err) {
    // Idem.
  }

  if (!anySucceeded) {
    error.value = "Impossible de lancer ce test (historique de prix/signaux insuffisant sur la periode choisie ?).";
  } else {
    results.value = merged;
  }
  isRunning.value = false;
}

function resetToDefaults() {
  smaParams.n1 = 10;
  smaParams.n2 = 20;
  rsiParams.period = 14;
  rsiParams.oversold = 30;
  rsiParams.overbought = 70;
  macdParams.fast = 12;
  macdParams.slow = 26;
  macdParams.signal = 9;
  bollingerParams.period = 20;
  bollingerParams.num_std = 2.0;
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

    <button class="text-xs text-blue-600 hover:underline mb-3 block" @click="showGuide = !showGuide">
      {{ showGuide ? "▾" : "▸" }} Comment lire ces resultats ? (guide pour debutant)
    </button>
    <div v-if="showGuide" class="mb-3 bg-blue-50 border border-blue-100 rounded p-3 space-y-2">
      <div v-for="section in GUIDE_SECTIONS" :key="section.title">
        <p class="text-xs font-semibold text-gray-700">{{ section.title }}</p>
        <p class="text-xs text-gray-600 leading-relaxed">{{ section.text }}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
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

    <button class="text-xs text-gray-600 hover:underline mb-2 block" @click="showBenchmarks = !showBenchmarks">
      {{ showBenchmarks ? "▾" : "▸" }} Autres benchmarks (RSI / MACD / Bollinger) - paramètres modulables
    </button>
    <div v-if="showBenchmarks" class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3 bg-white border rounded p-3">
      <div>
        <p class="text-xs font-semibold text-gray-600 mb-1">RSI (retour a la moyenne)</p>
        <div class="flex flex-col gap-1">
          <label class="text-xs text-gray-500 flex items-center justify-between gap-1">
            Periode
            <input v-model="rsiParams.period" type="number" min="2" class="border rounded px-2 py-1 text-sm w-20" />
          </label>
          <label class="text-xs text-gray-500 flex items-center justify-between gap-1">
            Survente
            <input v-model="rsiParams.oversold" type="number" min="0" max="100" class="border rounded px-2 py-1 text-sm w-20" />
          </label>
          <label class="text-xs text-gray-500 flex items-center justify-between gap-1">
            Surachat
            <input v-model="rsiParams.overbought" type="number" min="0" max="100" class="border rounded px-2 py-1 text-sm w-20" />
          </label>
        </div>
      </div>
      <div>
        <p class="text-xs font-semibold text-gray-600 mb-1">MACD (croisement)</p>
        <div class="flex flex-col gap-1">
          <label class="text-xs text-gray-500 flex items-center justify-between gap-1">
            Rapide
            <input v-model="macdParams.fast" type="number" min="1" class="border rounded px-2 py-1 text-sm w-20" />
          </label>
          <label class="text-xs text-gray-500 flex items-center justify-between gap-1">
            Lente
            <input v-model="macdParams.slow" type="number" min="1" class="border rounded px-2 py-1 text-sm w-20" />
          </label>
          <label class="text-xs text-gray-500 flex items-center justify-between gap-1">
            Signal
            <input v-model="macdParams.signal" type="number" min="1" class="border rounded px-2 py-1 text-sm w-20" />
          </label>
        </div>
      </div>
      <div>
        <p class="text-xs font-semibold text-gray-600 mb-1">Bollinger (retour a la moyenne)</p>
        <div class="flex flex-col gap-1">
          <label class="text-xs text-gray-500 flex items-center justify-between gap-1">
            Periode
            <input v-model="bollingerParams.period" type="number" min="2" class="border rounded px-2 py-1 text-sm w-20" />
          </label>
          <label class="text-xs text-gray-500 flex items-center justify-between gap-1">
            Ecarts-types
            <input v-model="bollingerParams.num_std" type="number" step="0.1" min="0.1" class="border rounded px-2 py-1 text-sm w-20" />
          </label>
        </div>
      </div>
    </div>

    <button class="text-xs text-gray-600 hover:underline mb-2 block" @click="showAdvanced = !showAdvanced">
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

    <!-- Tableau transpose : une metrique par ligne (avec explication au survol),
         un resultat (strategie x horizon) par colonne - plus lisible que 24
         colonnes cote a cote. Survole le nom d'une metrique pour son explication. -->
    <div v-if="groupedResults.length" class="border rounded bg-white overflow-x-auto">
      <table class="w-full text-xs">
        <thead class="bg-gray-50 text-gray-500 uppercase">
          <tr>
            <th class="text-left px-2 py-1.5 sticky left-0 bg-gray-50">Metrique</th>
            <th
              v-for="row in groupedResults"
              :key="`${row.strategy_name}-${row.horizon}`"
              class="text-right px-2 py-1.5 whitespace-nowrap cursor-help"
              :title="STRATEGY_GLOSSARY[row.strategy_name]"
            >
              {{ strategyLabel(row.strategy_name) }}
              <span class="block text-gray-400 normal-case">{{ row.horizon }}</span>
              <button
                v-if="row.plot_html"
                class="block mt-1 text-[10px] normal-case font-normal text-blue-600 hover:underline ml-auto"
                @click="togglePlot(row)"
              >
                {{ activePlotKey === resultKey(row) ? "Masquer le graphique" : "Voir le graphique" }}
              </button>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y">
          <template v-for="group in METRIC_GROUPS" :key="group.title">
            <tr class="bg-gray-50">
              <td :colspan="1 + groupedResults.length" class="px-2 py-1 font-semibold text-gray-600">
                {{ group.title }}
              </td>
            </tr>
            <template v-for="metric in group.rows" :key="metric.key">
              <tr>
                <td class="px-2 py-1.5 text-gray-700 whitespace-nowrap sticky left-0 bg-white">
                  <div class="flex items-center gap-1">
                    <span>{{ metric.label }}</span>
                    <button
                      class="w-4 h-4 shrink-0 rounded-full border border-gray-300 text-gray-400 text-[10px] leading-none hover:bg-blue-50 hover:text-blue-600 hover:border-blue-300"
                      :aria-expanded="openInfoKey === metric.key"
                      :title="'Explication : ' + metric.label"
                      @click="toggleInfo(metric.key)"
                    >
                      ?
                    </button>
                  </div>
                </td>
                <td v-for="row in groupedResults" :key="`${row.strategy_name}-${row.horizon}-${metric.key}`" class="px-2 py-1.5 text-right">
                  {{ formatMetric(row, metric) }}
                  <span
                    v-if="metricInterpretation(row, metric)"
                    class="block text-[10px] mt-0.5 px-1 rounded border w-fit ml-auto"
                    :class="toneClasses(metricInterpretation(row, metric).tone)"
                    :title="metricInterpretation(row, metric).label"
                  >
                    {{ metricInterpretation(row, metric).label }}
                  </span>
                </td>
              </tr>
              <tr v-if="openInfoKey === metric.key">
                <td :colspan="1 + groupedResults.length" class="px-2 py-2 bg-blue-50 text-gray-600 text-[11px] leading-relaxed">
                  {{ METRIC_GLOSSARY[metric.key] }}
                </td>
              </tr>
            </template>
          </template>
        </tbody>
      </table>
    </div>
    <p v-if="results && !groupedResults.length" class="text-xs text-gray-400">
      Aucun resultat - historique de prix/signaux insuffisant sur cette periode pour cet actif.
    </p>

    <!-- Synthese en langage clair (01/08/2026, voir constants/backtestingGlossary.js::
         buildSynthesis) : complement du tableau detaille, pour un lecteur qui veut
         comprendre le resultat sans dechiffrer 24 lignes de chiffres. -->
    <div v-if="groupedResults.length" class="mt-3 space-y-2">
      <p class="text-xs font-semibold text-gray-600">Resume en langage clair</p>
      <div v-for="row in groupedResults" :key="`synthesis-${resultKey(row)}`" class="border rounded bg-white p-2">
        <p class="text-xs font-medium text-gray-700 mb-1">
          {{ strategyLabel(row.strategy_name) }} <span class="text-gray-400 font-normal">{{ row.horizon }}</span>
        </p>
        <p v-if="buildSynthesis(row)" class="text-xs text-gray-600 leading-relaxed">{{ buildSynthesis(row) }}</p>
        <p v-else class="text-xs text-gray-400">Donnees insuffisantes pour generer un resume.</p>

        <!-- 13/08/2026 : contexte historique du scorecard hebdomadaire -
             replace ce SEUL run dans la duree, plutot que de le juger isolement
             (voir /fiabilite pour le detail complet par strategie/horizon). -->
        <div v-if="historicalStats(row)" class="mt-2 pt-2 border-t border-gray-100">
          <p class="text-[11px] text-gray-500 mb-1">
            Historique de cette strategie (evaluee automatiquement chaque semaine sur tout ton portefeuille - pas
            seulement ce run ponctuel) :
          </p>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="w in ['90d', '365d']"
              :key="w"
              class="text-[11px] px-1.5 py-0.5 rounded border cursor-help"
              :class="toneClasses(classifyScorecardConfidence(historicalStats(row).windows[w]?.count ?? 0).tone)"
              :title="classifyScorecardConfidence(historicalStats(row).windows[w]?.count ?? 0).label"
            >
              {{ w === "90d" ? "90j" : "12 mois" }} : {{ fmtHistWinRate(historicalStats(row).windows[w]) }} de reussite
              ({{ historicalStats(row).windows[w]?.count ?? 0 }} test{{ (historicalStats(row).windows[w]?.count ?? 0) > 1 ? "s" : "" }})
            </span>
          </div>
        </div>
        <p v-else class="text-[11px] text-gray-400 mt-2 pt-2 border-t border-gray-100 italic">
          Pas encore d'historique pour cette strategie/horizon - le job hebdomadaire d'evaluation n'a pas encore
          tourne, ou aucune position du portefeuille n'y correspond. Voir la page "Fiabilite" pour le detail complet.
        </p>
      </div>
    </div>

    <!-- Graphique interactif bt.plot() (01/08/2026, voir kernc_engine.py::_render_plot_html) :
         HTML standalone genere par backtesting.py, affiche via srcdoc dans un iframe isole
         (evite tout conflit CSS/JS avec le reste de l'app). Un seul graphique a la fois. -->
    <div v-if="activePlotResult" class="mt-3 border rounded bg-white">
      <div class="flex items-center justify-between px-2 py-1.5 border-b bg-gray-50">
        <p class="text-xs text-gray-600">
          Graphique - {{ strategyLabel(activePlotResult.strategy_name) }}
          <span class="text-gray-400">{{ activePlotResult.horizon }}</span>
        </p>
        <button class="text-xs text-gray-500 hover:underline" @click="activePlotKey = null">Fermer</button>
      </div>
      <iframe :srcdoc="activePlotResult.plot_html" class="w-full border-0" style="height: 600px" sandbox="allow-scripts"></iframe>
    </div>
  </div>
</template>
