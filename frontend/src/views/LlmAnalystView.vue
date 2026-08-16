<script setup>
// Analyste IA (16/08/2026, voir docs/20-instance-locale-pc-mac.md) - page
// reservee a une instance locale PC/Mac avec Ollama installe. `store.status`
// vient du backend a l'execution : si `enabled` est false (cas du NAS
// deploye, ou d'Ollama non configure), la page affiche un message
// explicatif et rien d'autre - meme garde-fou que le backend
// (router.py::require_enabled), en double ici par prudence (l'utilisateur
// pourrait arriver sur cette URL directement, ex. favori enregistre).
import { onBeforeUnmount, onMounted, ref } from "vue";
import AssetAutocomplete from "../components/AssetAutocomplete.vue";
import { useLlmAnalystStore } from "../stores/llmAnalyst";

const store = useLlmAnalystStore();

const selectedAsset = ref(null);
const strategyName = ref("sma_cross");
const modelName = ref("");

function isoDaysAgo(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}
const periodStart = ref(isoDaysAgo(365));
const periodEnd = ref(isoDaysAgo(0));

let pollTimer = null;

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function onLaunch() {
  if (!selectedAsset.value) return;
  stopPolling();
  store.reset();
  const job = await store.startAnalysis(
    selectedAsset.value.id,
    strategyName.value,
    periodStart.value,
    periodEnd.value,
    modelName.value.trim() || null
  );
  if (!job) return;
  pollTimer = setInterval(async () => {
    const updated = await store.pollJob(job.id);
    if (updated && (updated.status === "completed" || updated.status === "failed")) {
      stopPolling();
    }
  }, 3000);
}

onBeforeUnmount(stopPolling);

onMounted(async () => {
  await store.loadStatus();
  if (store.status?.enabled) {
    await store.loadStrategies();
  }
});

function statusClass(status) {
  if (status === "completed") return "bg-emerald-50 text-emerald-700 border-emerald-300";
  if (status === "failed") return "bg-red-50 text-red-700 border-red-300";
  if (status === "running") return "bg-amber-50 text-amber-700 border-amber-300";
  return "bg-gray-100 text-gray-500 border-gray-300";
}

const STRATEGY_LABELS = {
  sma_cross: "Croisement de moyennes mobiles (SMA)",
  rsi_mean_reversion: "Retour a la moyenne (RSI)",
  macd_cross: "Croisement MACD",
  bollinger_reversion: "Retour a la moyenne (Bandes de Bollinger)",
  buy_and_hold: "Achat et conservation (référence)",
};
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <div>
      <h1 class="text-xl font-semibold">Analyste IA (backtest)</h1>
      <p class="text-sm text-gray-500 mt-1">
        Fait rejouer un backtest et demande a un modele de langage local (Ollama, gratuit et installe sur ton
        PC/Mac) de rediger une synthese en francais - chaque affirmation cite les transactions exactes sur
        lesquelles elle s'appuie, verifiees automatiquement. Ne constitue jamais un conseil en investissement.
      </p>
    </div>

    <div v-if="store.isLoadingStatus" class="text-sm text-gray-400">Verification de la disponibilite...</div>

    <div v-else-if="!store.status?.enabled" class="bg-amber-50 border border-amber-200 rounded p-4 text-sm text-amber-900">
      <p class="font-medium">Fonctionnalite non disponible sur cette instance.</p>
      <p class="mt-1">
        L'analyste IA est reserve a une installation locale sur PC/Mac avec
        <a href="https://ollama.com" target="_blank" rel="noopener" class="underline">Ollama</a> installe -
        jamais actif sur le NAS deploye (pas de GPU disponible la-bas). Voir
        <code class="bg-amber-100 px-1 rounded">docs/20-instance-locale-pc-mac.md</code> dans le depot pour
        l'installer chez toi.
      </p>
    </div>

    <template v-else>
      <div class="bg-white border rounded p-4 space-y-4">
        <div>
          <label class="text-xs font-medium text-gray-600">Actif</label>
          <AssetAutocomplete @select="(a) => (selectedAsset = a)" />
          <p v-if="selectedAsset" class="text-xs text-gray-500 mt-1">
            Selectionne : <span class="font-medium">{{ selectedAsset.ticker }}</span> - {{ selectedAsset.name }}
          </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="text-xs font-medium text-gray-600">Strategie</label>
            <select v-model="strategyName" class="w-full border rounded px-3 py-2 text-sm mt-1">
              <option v-for="s in store.strategies" :key="s" :value="s">{{ STRATEGY_LABELS[s] || s }}</option>
            </select>
          </div>
          <div>
            <label class="text-xs font-medium text-gray-600">
              Modele Ollama <span class="text-gray-400">(defaut : {{ store.status.ollama_model }})</span>
            </label>
            <input v-model="modelName" type="text" :placeholder="store.status.ollama_model" class="w-full border rounded px-3 py-2 text-sm mt-1" />
          </div>
          <div>
            <label class="text-xs font-medium text-gray-600">Debut de periode</label>
            <input v-model="periodStart" type="date" class="w-full border rounded px-3 py-2 text-sm mt-1" />
          </div>
          <div>
            <label class="text-xs font-medium text-gray-600">Fin de periode</label>
            <input v-model="periodEnd" type="date" class="w-full border rounded px-3 py-2 text-sm mt-1" />
          </div>
        </div>

        <button
          class="border rounded px-4 py-2 text-sm bg-slate-900 text-white disabled:opacity-40"
          :disabled="!selectedAsset || store.isStarting || (store.job && ['pending', 'running'].includes(store.job.status))"
          @click="onLaunch"
        >
          {{ store.job && ["pending", "running"].includes(store.job.status) ? "Analyse en cours..." : "Lancer l'analyse" }}
        </button>

        <p v-if="store.error" class="text-xs text-red-600">{{ store.error }}</p>
      </div>

      <div v-if="store.job" class="bg-white border rounded p-4 space-y-3">
        <div class="flex items-center gap-2">
          <span class="text-xs font-medium">Statut :</span>
          <span class="text-xs px-2 py-0.5 rounded border" :class="statusClass(store.job.status)">{{ store.job.status }}</span>
        </div>

        <p v-if="store.job.status === 'failed'" class="text-xs text-red-600">
          Echec de l'analyse : {{ store.job.error_message }}
        </p>

        <template v-if="store.job.status === 'completed' && store.job.result">
          <div class="flex flex-wrap gap-2 text-xs">
            <span v-if="store.job.result.low_sample_warning" class="px-2 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-300">
              Echantillon faible
            </span>
            <span v-if="store.job.result.from_cache" class="px-2 py-0.5 rounded border bg-gray-100 text-gray-500 border-gray-300">
              Reponse en cache
            </span>
            <span v-if="store.job.result.citation_warnings?.length" class="px-2 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-300">
              {{ store.job.result.citation_warnings.length }} avertissement(s) de verification
            </span>
          </div>

          <pre class="whitespace-pre-wrap font-sans text-sm border-t pt-3 leading-relaxed">{{ store.job.result.markdown }}</pre>
        </template>
      </div>
    </template>
  </div>
</template>
