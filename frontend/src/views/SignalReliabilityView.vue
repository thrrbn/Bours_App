<script setup>
// Scorecard de fiabilite reelle des signaux (13/08/2026, voir
// backend/app/domains/signal_reliability/) - demande explicite de
// l'utilisateur : "un vrai score card de fiabilite historique du moteur de
// regles / pas juste du backtest". Alimente automatiquement chaque jour
// (job evaluate_signal_outcomes_job) : cette page n'affiche que le resultat
// deja calcule, aucun bouton "recalculer" ici (voir ParamsLabPanel.vue pour
// le backtest a la demande, qui reste le bon outil pour tester des variantes).
import { onMounted } from "vue";
import { useSignalReliabilityStore } from "../stores/signalReliability";
import { useStrategyScorecardStore } from "../stores/strategyScorecard";

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

function strategyLabel(name) {
  if (name === "internal_rules") return "Moteur interne (regles)";
  if (name === "signal_replay") return "Nos signaux (signal_replay)";
  if (name === "sma_cross") return "Croisement SMA";
  if (name === "rsi_mean_reversion") return "RSI";
  if (name === "macd_cross") return "MACD";
  if (name === "bollinger_reversion") return "Bollinger";
  if (name === "buy_and_hold") return "Buy & hold";
  return name || "n/d";
}

function fmtWinRate(stats) {
  if (!stats || stats.avg_win_rate === null || stats.avg_win_rate === undefined) return "n/d";
  return `${(stats.avg_win_rate * 100).toFixed(0)}%`;
}

function fmtReturn(stats) {
  if (!stats || stats.avg_return_pct === null || stats.avg_return_pct === undefined) return "n/d";
  return `${stats.avg_return_pct >= 0 ? "+" : ""}${stats.avg_return_pct.toFixed(1)}%`;
}
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
      portefeuille virtuel - pour voir son evolution dans la duree plutot qu'un seul test ponctuel.
    </p>

    <p v-if="strategyStore.isLoading" class="text-sm text-gray-500">Chargement...</p>
    <p v-if="strategyStore.error" class="text-sm text-red-600">{{ strategyStore.error }}</p>

    <template v-if="strategyStore.scorecard">
      <p class="text-xs text-gray-400 mb-4">
        Dernier calcul : {{ fmtDate(strategyStore.scorecard.last_evaluated_at) }}
      </p>

      <div v-if="strategyStore.scorecard.results.length" class="border rounded bg-white overflow-x-auto mb-3">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th class="text-left px-3 py-2 font-medium">Strategie</th>
              <th v-for="w in STRATEGY_WINDOW_ORDER" :key="w" class="text-right px-3 py-2 font-medium">
                {{ STRATEGY_WINDOW_LABELS[w] }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="row in strategyStore.scorecard.results" :key="`${row.strategy_name}-${row.horizon}`">
              <td class="px-3 py-2 font-medium">
                {{ strategyLabel(row.strategy_name) }}
                <span v-if="row.horizon !== 'n/a'" class="text-xs text-gray-400 block">{{ HORIZON_LABELS[row.horizon] || row.horizon }}</span>
              </td>
              <td v-for="w in STRATEGY_WINDOW_ORDER" :key="w" class="px-3 py-2 text-right">
                <span class="font-mono font-semibold">{{ fmtWinRate(row.windows[w]) }}</span>
                <span class="text-xs text-gray-400 block">reussite ({{ row.windows[w]?.count ?? 0 }} test(s))</span>
                <span v-if="row.windows[w] && row.windows[w].avg_return_pct !== null" class="text-xs text-gray-500 block">
                  rendement moyen : {{ fmtReturn(row.windows[w]) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="text-xs text-gray-400 mb-3">
        Aucune evaluation encore disponible - normal juste apres l'activation de cette fonctionnalite : le job
        hebdomadaire n'a pas encore tourne, ou aucune position n'est encore suivie dans le portefeuille virtuel.
      </p>

      <p class="text-xs text-gray-400 italic">{{ strategyStore.scorecard.disclaimer }}</p>
    </template>
  </div>
</template>
