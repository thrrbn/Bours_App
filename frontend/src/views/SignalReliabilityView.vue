<script setup>
// Scorecard de fiabilite reelle des signaux (13/08/2026, voir
// backend/app/domains/signal_reliability/) - demande explicite de
// l'utilisateur : "un vrai score card de fiabilite historique du moteur de
// regles / pas juste du backtest". Alimente automatiquement chaque jour
// (job evaluate_signal_outcomes_job) : cette page n'affiche que le resultat
// deja calcule, aucun bouton "recalculer" ici (voir ParamsLabPanel.vue pour
// le backtest a la demande, qui reste le bon outil pour tester des variantes).
import { computed, onMounted, ref } from "vue";
import { useSignalReliabilityStore } from "../stores/signalReliability";
import { useStrategyScorecardStore } from "../stores/strategyScorecard";
import { classifyScorecardConfidence, toneClasses } from "../constants/backtestingGlossary";

const store = useSignalReliabilityStore();
const strategyStore = useStrategyScorecardStore();

onMounted(() => {
  store.load();
  strategyStore.load();
});

const HORIZON_LABELS = { short: "Court terme", medium: "Moyen terme", long: "Long terme" };
const WINDOW_LABELS = { "30d": "30 derniers jours", "90d": "90 derniers jours", "365d": "12 derniers mois", all: "Tout l'historique" };
const WINDOW_ORDER = ["30d", "90d", "365d", "all"];

function fmtPrecision(stats) {
  if (!stats || stats.precision === null || stats.precision === undefined) return "n/d";
  return `${(stats.precision * 100).toFixed(0)}%`;
}

function fmtDate(iso) {
  if (!iso) return "jamais encore";
  return new Date(iso).toLocaleString();
}

// Scorecard par strategie (13/08/2026) - meme etiquettes que ParamsLabPanel.vue::
// strategyLabel (dupliquees volontairement, composants independants).
const STRATEGY_WINDOW_LABELS = { "90d": "90 derniers jours", "365d": "12 derniers mois", all: "Tout l'historique" };
const STRATEGY_WINDOW_ORDER = ["90d", "365d", "all"];

// 14/08/2026 : internal_rules et signal_replay sont desormais aussi
// evalues chaque semaine avec 2 profils de decision predefinis en plus du
// profil par defaut (voir backend/app/jobs/evaluate_strategies_job.py::
// DECISION_PROFILES) - le backend suffixe strategy_name ("internal_rules::
// prudent") pour que chaque profil reste une ligne distincte et comparable
// dans le classement ci-dessous, plutot que d'ajouter une dimension separee
// au tableau.
const BASE_STRATEGY_LABELS = {
  internal_rules: "Moteur interne (regles)",
  signal_replay: "Nos signaux (signal_replay)",
  sma_cross: "Croisement SMA",
  rsi_mean_reversion: "RSI",
  macd_cross: "MACD",
  bollinger_reversion: "Bollinger",
  buy_and_hold: "Buy & hold",
};

const PROFILE_LABELS = { prudent: "profil prudent", agressif: "profil agressif" };

function strategyLabel(name) {
  if (!name) return "n/d";
  const [base, profile] = name.split("::");
  const baseLabel = BASE_STRATEGY_LABELS[base] || base;
  return profile ? `${baseLabel} - ${PROFILE_LABELS[profile] || profile}` : baseLabel;
}

function fmtWinRate(stats) {
  if (!stats || stats.avg_win_rate === null || stats.avg_win_rate === undefined) return "n/d";
  return `${(stats.avg_win_rate * 100).toFixed(0)}%`;
}

function fmtReturn(stats) {
  if (!stats || stats.avg_return_pct === null || stats.avg_return_pct === undefined) return "n/d";
  return `${stats.avg_return_pct >= 0 ? "+" : ""}${stats.avg_return_pct.toFixed(1)}%`;
}

// 13/08/2026 : "arbitrer entre strategies plutot que de juger sur un seul
// backtest" - classement triable par fenetre, plutot qu'un tableau statique
// dans l'ordre alphabetique. Les lignes horizon="n/a" (SMA/RSI/MACD/
// Bollinger/buy&hold) et les horizons court/moyen/long (moteur interne,
// signal_replay) ne sont pas strictement comparables entre elles - le tri
// reste indicatif (voir horizon affiche sur chaque ligne), pas un
// classement absolu.
const sortWindow = ref("365d");

const sortedStrategyResults = computed(() => {
  const results = strategyStore.scorecard?.results ?? [];
  return [...results].sort((a, b) => {
    const aWinRate = a.windows[sortWindow.value]?.avg_win_rate;
    const bWinRate = b.windows[sortWindow.value]?.avg_win_rate;
    if (aWinRate === null || aWinRate === undefined) return 1;
    if (bWinRate === null || bWinRate === undefined) return -1;
    return bWinRate - aWinRate;
  });
});
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <h2 class="text-xl font-semibold mb-2">Fiabilite du moteur de signal</h2>
    <p class="text-sm text-gray-500 mb-4">
      Precision REELLE du moteur de regles sur les signaux deja calcules et arrives a echeance - alimentee
      automatiquement chaque jour, pas un backtest a la demande (pour ça, voir "tester les parametres" sur une
      position du portefeuille).
    </p>

    <p v-if="store.isLoading" class="text-sm text-gray-500">Chargement...</p>
    <p v-if="store.error" class="text-sm text-red-600">{{ store.error }}</p>

    <template v-if="store.scorecard">
      <p class="text-xs text-gray-400 mb-4">Dernier calcul : {{ fmtDate(store.scorecard.last_evaluated_at) }}</p>

      <div class="border rounded bg-white overflow-x-auto mb-3">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th class="text-left px-3 py-2 font-medium">Horizon</th>
              <th v-for="w in WINDOW_ORDER" :key="w" class="text-right px-3 py-2 font-medium">{{ WINDOW_LABELS[w] }}</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="(label, horizon) in HORIZON_LABELS" :key="horizon">
              <td class="px-3 py-2 font-medium">{{ label }}</td>
              <td v-for="w in WINDOW_ORDER" :key="w" class="px-3 py-2 text-right">
                <span class="font-mono font-semibold">{{ fmtPrecision(store.scorecard.horizons[horizon]?.[w]) }}</span>
                <span class="text-xs text-gray-400 block">
                  {{ store.scorecard.horizons[horizon]?.[w]?.count ?? 0 }} signal(aux) evalue(s)
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p
        v-if="Object.values(store.scorecard.horizons).every((h) => Object.values(h).every((w) => w.count === 0))"
        class="text-xs text-gray-400 mb-3"
      >
        Aucun signal encore evalue - normal juste apres l'activation de cette fonctionnalite : un signal ne peut
        etre evalue qu'une fois son horizon ecoule (5 jours pour le court terme, jusqu'a 60 jours pour le long
        terme), et le job d'evaluation tourne une fois par jour.
      </p>

      <p class="text-xs text-gray-400 italic">{{ store.scorecard.disclaimer }}</p>
    </template>

    <h2 class="text-xl font-semibold mb-2 mt-10">Fiabilite des strategies de backtest</h2>
    <p class="text-sm text-gray-500 mb-4">
      Chaque strategie testable dans "tester les parametres" (SMA, RSI, MACD, Bollinger, nos signaux, moteur
      interne) est rejouee automatiquement chaque semaine avec ses parametres par defaut, sur les positions du
      portefeuille virtuel - pour arbitrer entre strategies sur leur tendance dans la duree, plutot que de juger
      sur un seul test ponctuel (voir "tester les parametres" sur une position pour ce test ponctuel, qui affiche
      desormais aussi ce meme historique en contexte). Le moteur interne et nos signaux sont en plus rejoues avec
      2 profils de decision predefinis (prudent, agressif) en plus du profil par defaut - classe-les par fenetre
      ci-dessous pour voir lequel a le mieux performe dans la duree, sans jamais optimiser sur une periode deja
      connue.
    </p>

    <p v-if="strategyStore.isLoading" class="text-sm text-gray-500">Chargement...</p>
    <p v-if="strategyStore.error" class="text-sm text-red-600">{{ strategyStore.error }}</p>

    <template v-if="strategyStore.scorecard">
      <div class="flex items-center justify-between mb-2">
        <p class="text-xs text-gray-400">Dernier calcul : {{ fmtDate(strategyStore.scorecard.last_evaluated_at) }}</p>
        <label class="text-xs text-gray-500 flex items-center gap-1.5">
          Classer par
          <select v-model="sortWindow" class="border rounded px-1.5 py-1 text-xs">
            <option v-for="w in STRATEGY_WINDOW_ORDER" :key="w" :value="w">{{ STRATEGY_WINDOW_LABELS[w] }}</option>
          </select>
        </label>
      </div>

      <div v-if="strategyStore.scorecard.results.length" class="border rounded bg-white overflow-x-auto mb-1">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th class="text-left px-3 py-2 font-medium">#</th>
              <th class="text-left px-3 py-2 font-medium">Strategie</th>
              <th v-for="w in STRATEGY_WINDOW_ORDER" :key="w" class="text-right px-3 py-2 font-medium">
                {{ STRATEGY_WINDOW_LABELS[w] }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="(row, idx) in sortedStrategyResults" :key="`${row.strategy_name}-${row.horizon}`">
              <td class="px-3 py-2 text-gray-400 text-xs align-top">{{ idx + 1 }}</td>
              <td class="px-3 py-2 font-medium align-top">
                {{ strategyLabel(row.strategy_name) }}
                <span v-if="row.horizon !== 'n/a'" class="text-xs text-gray-400 block">{{ HORIZON_LABELS[row.horizon] || row.horizon }}</span>
              </td>
              <td v-for="w in STRATEGY_WINDOW_ORDER" :key="w" class="px-3 py-2 text-right align-top">
                <span class="font-mono font-semibold">{{ fmtWinRate(row.windows[w]) }}</span>
                <span class="text-xs text-gray-400 block">reussite</span>
                <span v-if="row.windows[w] && row.windows[w].avg_return_pct !== null" class="text-xs text-gray-500 block">
                  rendement moyen : {{ fmtReturn(row.windows[w]) }}
                </span>
                <span
                  class="inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] border cursor-help"
                  :class="toneClasses(classifyScorecardConfidence(row.windows[w]?.count ?? 0).tone)"
                  :title="classifyScorecardConfidence(row.windows[w]?.count ?? 0).label"
                >
                  {{ row.windows[w]?.count ?? 0 }} test{{ (row.windows[w]?.count ?? 0) > 1 ? "s" : "" }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="strategyStore.scorecard.results.length" class="text-xs text-gray-400 mb-3">
        Classement indicatif : le moteur interne et "nos signaux" varient par horizon (court/moyen/long), les
        benchmarks (SMA, RSI, MACD, Bollinger, buy &amp; hold) sont independants de l'horizon - compare d'abord des
        lignes avec un echantillon suffisant (badge ci-dessus) avant de tirer une conclusion.
      </p>
      <p v-else class="text-xs text-gray-400 mb-3">
        Aucune evaluation encore disponible - normal juste apres l'activation de cette fonctionnalite : le job
        hebdomadaire n'a pas encore tourne, ou aucune position n'est encore suivie dans le portefeuille virtuel.
      </p>

      <p class="text-xs text-gray-400 italic">{{ strategyStore.scorecard.disclaimer }}</p>
    </template>
  </div>
</template>
