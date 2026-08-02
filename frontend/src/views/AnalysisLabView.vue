<script setup>
// Bac a sable pedagogique (31/07/2026, voir docs/STACK.md, domaine
// analysis_lab) : vue en LECTURE SEULE, aucun appel ici ne modifie un
// signal officiel, une position de portefeuille ou un backtest. Objectif
// explicite de l'utilisateur : comprendre "sur quelle base" un modele
// calcule (indicateurs techniques bruts) et comparer des approches
// classiques (Random Forest, XGBoost, ARIMA) au moteur de regles reel deja
// affiche ailleurs dans l'app - jamais un signal a suivre.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useAnalysisLabStore } from "../stores/analysisLab";
import AssetAutocomplete from "../components/AssetAutocomplete.vue";
import HorizonTabs from "../components/HorizonTabs.vue";
import {
  AGREEMENT_GLOSSARY,
  DIRECTION_GLOSSARY,
  JOB_STATUS_GLOSSARY,
  METRIC_GLOSSARY,
  MODEL_GLOSSARY,
  REAL_SIGNAL_GLOSSARY,
  STATUS_GLOSSARY,
  explainFeature,
  interpretFeature,
  toneClasses,
} from "../constants/analysisLabGlossary";

const store = useAnalysisLabStore();
const router = useRouter();

const tab = ref("asset"); // 'asset' | 'portfolio'
const selectedAsset = ref(null);
const horizon = ref("medium");
const portfolioHorizon = ref("medium");
const featureFilter = ref("");
const showAllFeatures = ref(false);

// Phase 3 (31/07/2026) : LSTM asynchrone (voir docs/STACK.md) - le job tourne
// en tache de fond cote backend, cette vue interroge son statut toutes les 2s
// jusqu'a completion/echec plutot que de bloquer sur la requete initiale.
let deepPollTimer = null;

function stopDeepPolling() {
  if (deepPollTimer) {
    clearInterval(deepPollTimer);
    deepPollTimer = null;
  }
}

async function onTrainDeep() {
  if (!selectedAsset.value) return;
  stopDeepPolling();
  const job = await store.startDeepTraining(selectedAsset.value.id, "lstm", horizon.value);
  if (!job) return;
  deepPollTimer = setInterval(async () => {
    const updated = await store.pollDeepJob(job.id);
    if (updated && (updated.status === "completed" || updated.status === "failed")) {
      stopDeepPolling();
    }
  }, 2000);
}

onBeforeUnmount(stopDeepPolling);

async function onSelectAsset(asset) {
  selectedAsset.value = asset;
  stopDeepPolling();
  store.reset();
  await Promise.all([store.loadFeatureSnapshot(asset.id), store.loadComparison(asset.id, horizon.value)]);
}

watch(horizon, async (h) => {
  stopDeepPolling();
  store.deepJob = null;
  if (selectedAsset.value) await store.loadComparison(selectedAsset.value.id, h);
});

async function onTabChange(next) {
  tab.value = next;
  if (next === "portfolio" && !store.portfolioComparison) {
    await store.loadPortfolioComparison(portfolioHorizon.value);
  }
}

watch(portfolioHorizon, async (h) => {
  if (tab.value === "portfolio") await store.loadPortfolioComparison(h);
});

const filteredFeatures = computed(() => {
  if (!store.featureSnapshot) return [];
  const entries = Object.entries(store.featureSnapshot.features);
  const filtered = featureFilter.value.trim()
    ? entries.filter(([name]) => name.toLowerCase().includes(featureFilter.value.trim().toLowerCase()))
    : entries;
  const sorted = filtered.sort((a, b) => a[0].localeCompare(b[0]));
  return showAllFeatures.value || featureFilter.value.trim() ? sorted : sorted.slice(0, 20);
});

// Liste des 72 noms d'indicateurs pour alimenter le <datalist> du filtre -
// sans ca, il faut deviner l'orthographe exacte (ex "rsi_14" vs "RSI14")
// avant de voir quoi que ce soit. Le navigateur propose ces noms au fur et a
// mesure de la frappe (autocomplete natif, aucune dependance JS).
const allFeatureNames = computed(() => {
  if (!store.featureSnapshot) return [];
  return Object.keys(store.featureSnapshot.features).sort((a, b) => a.localeCompare(b));
});

function fmtFeatureValue(value) {
  return value === null || value === undefined ? "n/d" : value;
}

function statusLabel(status) {
  if (status === "fiable") return "Fiable";
  if (status === "en_apprentissage") return "En apprentissage";
  return "Indisponible";
}

function statusClass(status) {
  if (status === "fiable") return "bg-emerald-50 text-emerald-700 border-emerald-300";
  if (status === "en_apprentissage") return "bg-amber-50 text-amber-700 border-amber-300";
  return "bg-gray-100 text-gray-500 border-gray-300";
}

function directionClass(direction) {
  if (direction === "hausse") return "bg-emerald-50 text-emerald-700 border-emerald-300";
  if (direction === "baisse") return "bg-red-50 text-red-700 border-red-300";
  return "bg-gray-100 text-gray-500 border-gray-300";
}

// Ordre d'affichage stable (Phase 2, 31/07/2026 : Prophet + vote d'ensemble
// ajoutes aux cotes de Random Forest/XGBoost/ARIMA - voir docs/STACK.md).
const MODEL_ORDER = ["random_forest", "xgboost", "arima", "prophet", "ensemble"];

function modelLabel(name) {
  if (name === "random_forest") return "Random Forest";
  if (name === "xgboost") return "XGBoost";
  if (name === "arima") return "ARIMA";
  if (name === "prophet") return "Prophet";
  if (name === "ensemble") return "Ensemble (vote)";
  return name;
}

function orderedModels(models) {
  return [...models].sort((a, b) => MODEL_ORDER.indexOf(a.model_name) - MODEL_ORDER.indexOf(b.model_name));
}

function goToAsset(assetId) {
  router.push({ name: "dashboard", params: { assetId } });
}
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <h2 class="text-xl font-semibold mb-1">Laboratoire d'analyse (pedagogique)</h2>
    <p class="text-xs text-gray-400 mb-4">
      Outil d'apprentissage : indicateurs techniques bruts et modeles legers (Random Forest, XGBoost, ARIMA)
      compares au signal reel deja calcule par le moteur de regles. Ne modifie jamais un signal, une position
      ou un backtest - ne constitue en aucun cas un conseil d'investissement.
    </p>

    <div class="flex gap-2 border-b border-gray-200 mb-6">
      <button
        class="px-3 py-2 text-sm border-b-2 transition-colors"
        :class="tab === 'asset' ? 'border-gray-900 font-medium' : 'border-transparent text-gray-500 hover:text-gray-800'"
        @click="onTabChange('asset')"
      >
        Par actif
      </button>
      <button
        class="px-3 py-2 text-sm border-b-2 transition-colors"
        :class="tab === 'portfolio' ? 'border-gray-900 font-medium' : 'border-transparent text-gray-500 hover:text-gray-800'"
        @click="onTabChange('portfolio')"
      >
        Sur le portefeuille virtuel
      </button>
    </div>

    <p v-if="store.error" class="text-sm text-red-600 mb-4">{{ store.error }}</p>

    <!-- Onglet "Par actif" -->
    <div v-if="tab === 'asset'">
      <div class="mb-4">
        <AssetAutocomplete @select="onSelectAsset" />
        <p v-if="selectedAsset" class="text-xs text-gray-500 mt-1">
          Selectionne : {{ selectedAsset.ticker }} - {{ selectedAsset.name }}
        </p>
      </div>

      <template v-if="selectedAsset">
        <HorizonTabs v-model="horizon" />

        <p v-if="store.isLoadingComparison" class="text-sm text-gray-500 mb-4">Entrainement des modeles...</p>

        <div v-if="store.comparison" class="mb-8">
          <h3 class="text-sm font-semibold mb-2">Signal reel (moteur de regles)</h3>
          <div v-if="store.comparison.real_signal" class="border rounded-lg p-3 bg-white mb-4 flex flex-wrap gap-4 text-sm">
            <span
              class="font-medium underline decoration-dotted decoration-gray-400 cursor-help"
              :title="REAL_SIGNAL_GLOSSARY[store.comparison.real_signal.final_signal]"
            >
              {{ store.comparison.real_signal.final_signal }}
            </span>
            <span
              class="text-gray-500 underline decoration-dotted decoration-gray-300 cursor-help"
              :title="REAL_SIGNAL_GLOSSARY.technical_score"
            >
              Technique : {{ store.comparison.real_signal.technical_score.toFixed(1) }}
            </span>
            <span
              class="text-gray-500 underline decoration-dotted decoration-gray-300 cursor-help"
              :title="REAL_SIGNAL_GLOSSARY.news_score"
            >
              News : {{ store.comparison.real_signal.news_score.toFixed(1) }}
            </span>
            <span
              class="text-gray-500 underline decoration-dotted decoration-gray-300 cursor-help"
              :title="REAL_SIGNAL_GLOSSARY.risk_score"
            >
              Risque : {{ store.comparison.real_signal.risk_score.toFixed(1) }}
            </span>
            <span
              class="text-gray-500 underline decoration-dotted decoration-gray-300 cursor-help"
              :title="REAL_SIGNAL_GLOSSARY.confidence_score"
            >
              Confiance : {{ store.comparison.real_signal.confidence_score.toFixed(1) }}
            </span>
            <span class="text-gray-400 text-xs">
              calcule le {{ new Date(store.comparison.real_signal.computed_at).toLocaleString() }}
            </span>
          </div>
          <p v-else class="text-sm text-gray-400 mb-4">Aucun signal reel calcule pour cet actif/horizon pour l'instant.</p>

          <h3 class="text-sm font-semibold mb-2">Modeles legers (bac a sable, jamais utilises comme signal officiel)</h3>
          <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div v-for="model in orderedModels(store.comparison.models)" :key="model.model_name" class="border rounded-lg p-3 bg-white">
              <div class="flex items-center justify-between mb-2">
                <span
                  class="font-medium text-sm underline decoration-dotted decoration-gray-400 cursor-help"
                  :title="MODEL_GLOSSARY[model.model_name]"
                >
                  {{ modelLabel(model.model_name) }}
                </span>
                <span
                  class="px-2 py-0.5 rounded-full text-xs font-medium border cursor-help"
                  :class="statusClass(model.model_status)"
                  :title="STATUS_GLOSSARY[model.model_status]"
                >
                  {{ statusLabel(model.model_status) }}
                </span>
              </div>
              <div v-if="model.predicted_direction" class="mb-2 flex items-center gap-2">
                <span
                  class="px-2 py-0.5 rounded-full text-xs font-medium border cursor-help"
                  :class="directionClass(model.predicted_direction)"
                  :title="DIRECTION_GLOSSARY[model.predicted_direction]"
                >
                  {{ model.predicted_direction }}
                </span>
                <span
                  v-if="model.probability_up !== null"
                  class="text-xs text-gray-500 underline decoration-dotted decoration-gray-300 cursor-help"
                  :title="METRIC_GLOSSARY.probability_up"
                >
                  {{ (model.probability_up * 100).toFixed(0) }}% de hausse estimee
                </span>
                <span v-if="model.agrees_with_real_signal === true" class="text-emerald-600 text-xs cursor-help" :title="AGREEMENT_GLOSSARY.true">✓ accord</span>
                <span v-else-if="model.agrees_with_real_signal === false" class="text-red-500 text-xs cursor-help" :title="AGREEMENT_GLOSSARY.false">✗ desaccord</span>
              </div>
              <p class="text-xs text-gray-500 mb-2">{{ model.explanation }}</p>
              <div v-if="model.validation_status === 'ok'" class="text-xs text-gray-400 mb-2">
                <span class="underline decoration-dotted decoration-gray-300 cursor-help" :title="METRIC_GLOSSARY.train_accuracy">
                  Train {{ (model.train_accuracy * 100).toFixed(0) }}%
                </span>
                /
                <span class="underline decoration-dotted decoration-gray-300 cursor-help" :title="METRIC_GLOSSARY.validation_accuracy">
                  validation {{ (model.validation_accuracy * 100).toFixed(0) }}%
                </span>
                sur {{ model.validation_sample_count }} exemples recents
              </div>
              <div v-if="Object.keys(model.feature_importance).length" class="text-xs">
                <span class="text-gray-400 underline decoration-dotted decoration-gray-300 cursor-help" :title="METRIC_GLOSSARY.feature_importance">Facteurs les plus influents :</span>
                <ul class="mt-1 space-y-0.5">
                  <li v-for="[name, weight] in Object.entries(model.feature_importance)" :key="name" class="flex justify-between">
                    <span
                      class="text-gray-600 underline decoration-dotted decoration-gray-300 cursor-help"
                      :title="explainFeature(name) || name"
                    >
                      {{ name }}
                    </span>
                    <span class="text-gray-400">{{ weight.toFixed(3) }}</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <div class="border rounded-lg p-3 bg-white mt-3">
            <div class="flex items-center justify-between mb-2">
              <span
                class="font-medium text-sm underline decoration-dotted decoration-gray-400 cursor-help"
                :title="MODEL_GLOSSARY.lstm"
              >
                LSTM (Phase 3, asynchrone)
              </span>
              <span
                v-if="store.deepJob"
                class="px-2 py-0.5 rounded-full text-xs font-medium border cursor-help"
                :class="statusClass(store.deepJob.status === 'completed' ? store.deepJob.result?.model_status : 'en_apprentissage')"
                :title="JOB_STATUS_GLOSSARY[store.deepJob.status]"
              >
                {{ store.deepJob.status }}
              </span>
            </div>
            <p class="text-xs text-gray-500 mb-2">
              Modele sequentiel entraine en tache de fond (quelques secondes) plutot qu'a la volee comme les modeles
              ci-dessus - reponse immediate ("pending"), le resultat arrive apres coup.
            </p>
            <button
              class="px-3 py-1.5 bg-gray-900 text-white rounded text-xs disabled:opacity-40"
              :disabled="store.deepJob && ['pending', 'running'].includes(store.deepJob.status)"
              @click="onTrainDeep"
            >
              {{ store.deepJob && ["pending", "running"].includes(store.deepJob.status) ? "Entrainement en cours..." : "Entrainer un LSTM" }}
            </button>

            <div v-if="store.deepJob && store.deepJob.status === 'completed' && store.deepJob.result" class="mt-3">
              <div class="flex items-center gap-2 mb-1">
                <span
                  v-if="store.deepJob.result.predicted_direction"
                  class="px-2 py-0.5 rounded-full text-xs font-medium border cursor-help"
                  :class="directionClass(store.deepJob.result.predicted_direction)"
                  :title="DIRECTION_GLOSSARY[store.deepJob.result.predicted_direction]"
                >
                  {{ store.deepJob.result.predicted_direction }}
                </span>
                <span
                  v-if="store.deepJob.result.probability_up !== null"
                  class="text-xs text-gray-500 underline decoration-dotted decoration-gray-300 cursor-help"
                  :title="METRIC_GLOSSARY.probability_up"
                >
                  {{ (store.deepJob.result.probability_up * 100).toFixed(0) }}% de hausse estimee
                </span>
                <span v-if="store.deepJob.result.agrees_with_real_signal === true" class="text-emerald-600 text-xs cursor-help" :title="AGREEMENT_GLOSSARY.true">✓ accord</span>
                <span v-else-if="store.deepJob.result.agrees_with_real_signal === false" class="text-red-500 text-xs cursor-help" :title="AGREEMENT_GLOSSARY.false">✗ desaccord</span>
              </div>
              <p class="text-xs text-gray-500">{{ store.deepJob.result.explanation }}</p>
              <div v-if="store.deepJob.result.validation_status === 'ok'" class="text-xs text-gray-400 mt-1">
                <span class="underline decoration-dotted decoration-gray-300 cursor-help" :title="METRIC_GLOSSARY.train_accuracy">
                  Train {{ (store.deepJob.result.train_accuracy * 100).toFixed(0) }}%
                </span>
                /
                <span class="underline decoration-dotted decoration-gray-300 cursor-help" :title="METRIC_GLOSSARY.validation_accuracy">
                  validation {{ (store.deepJob.result.validation_accuracy * 100).toFixed(0) }}%
                </span>
                sur {{ store.deepJob.result.validation_sample_count }} exemples recents
              </div>
            </div>
            <p v-else-if="store.deepJob && store.deepJob.status === 'failed'" class="text-xs text-red-600 mt-2">
              Echec de l'entrainement : {{ store.deepJob.error_message }}
            </p>
          </div>

          <p class="text-xs text-gray-400 italic mt-3">{{ store.comparison.disclaimer }}</p>
        </div>

        <div v-if="store.featureSnapshot">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-semibold">
              Indicateurs techniques ({{ store.featureSnapshot.feature_count }}, au {{ store.featureSnapshot.as_of_date }})
            </h3>
          </div>
          <input
            v-model="featureFilter"
            type="text"
            list="feature-name-suggestions"
            placeholder="Filtrer par nom (ex : rsi, bollinger, obv...) - tape pour voir les noms disponibles"
            class="border rounded px-3 py-2 text-sm w-full mb-2"
          />
          <datalist id="feature-name-suggestions">
            <option v-for="name in allFeatureNames" :key="name" :value="name" />
          </datalist>
          <p class="text-xs text-gray-400 mb-2">
            {{ allFeatureNames.length }} noms disponibles - commence a taper pour voir les suggestions du navigateur,
            ou <button class="underline hover:text-gray-600" @click="showAllFeatures = !showAllFeatures">{{ showAllFeatures ? "reduire" : "afficher la liste complete" }}</button>.
            Survole un nom d'indicateur (souligne en pointilles) pour voir son explication.
          </p>
          <p class="text-xs text-gray-400 mb-2">
            La colonne "Zone" situe la valeur dans sa fourchette de lecture usuelle, pour les indicateurs qui en ont
            une (oscillateurs bornes) - ce n'est jamais un signal d'achat/vente, juste un repere pour comprendre le
            chiffre.
          </p>
          <div class="border rounded bg-white overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th class="text-left px-3 py-2 font-medium">Indicateur</th>
                  <th class="text-right px-3 py-2 font-medium">Valeur</th>
                  <th class="text-right px-3 py-2 font-medium">Zone</th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <tr v-for="[name, value] in filteredFeatures" :key="name">
                  <td
                    class="px-3 py-1.5 text-gray-600 underline decoration-dotted decoration-gray-300 cursor-help"
                    :title="explainFeature(name) || name"
                  >
                    {{ name }}
                  </td>
                  <td class="px-3 py-1.5 text-right font-mono">{{ fmtFeatureValue(value) }}</td>
                  <td class="px-3 py-1.5 text-right">
                    <span
                      v-if="interpretFeature(name, value)"
                      class="px-2 py-0.5 rounded-full text-xs font-medium border cursor-help"
                      :class="toneClasses(interpretFeature(name, value).tone)"
                      :title="`Fourchette usuelle : ${interpretFeature(name, value).rangeNote}`"
                    >
                      {{ interpretFeature(name, value).label }}
                    </span>
                    <span v-else class="text-xs text-gray-300">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
      <p v-else class="text-sm text-gray-400">Choisis un actif ci-dessus pour explorer ses indicateurs et comparer les modeles.</p>
    </div>

    <!-- Onglet "Sur le portefeuille virtuel" -->
    <div v-else>
      <HorizonTabs v-model="portfolioHorizon" />
      <p v-if="store.isLoadingPortfolio" class="text-sm text-gray-500 mb-4">Entrainement des modeles sur chaque position...</p>

      <div v-if="store.portfolioComparison">
        <p v-if="!store.portfolioComparison.comparisons.length" class="text-sm text-gray-400 mb-4">
          Aucune position en portefeuille - achete un actif dans "Portefeuille virtuel" pour l'utiliser comme jeu de test ici.
        </p>
        <div v-else class="border rounded bg-white overflow-x-auto mb-4">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th class="text-left px-3 py-2">Actif</th>
                <th class="text-center px-3 py-2">Signal reel</th>
                <th
                  v-for="name in MODEL_ORDER"
                  :key="name"
                  class="text-center px-3 py-2 underline decoration-dotted decoration-gray-300 cursor-help"
                  :title="MODEL_GLOSSARY[name]"
                >
                  {{ modelLabel(name) }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y">
              <tr
                v-for="comp in store.portfolioComparison.comparisons"
                :key="comp.asset.id"
                class="hover:bg-gray-50 cursor-pointer"
                @click="goToAsset(comp.asset.id)"
              >
                <td class="px-3 py-2">
                  <span class="font-medium">{{ comp.asset.ticker }}</span>
                  <span class="text-gray-500 text-xs block">{{ comp.asset.name }}</span>
                </td>
                <td
                  class="px-3 py-2 text-center text-xs"
                  :class="{ 'underline decoration-dotted decoration-gray-300 cursor-help': comp.real_signal }"
                  :title="comp.real_signal ? REAL_SIGNAL_GLOSSARY[comp.real_signal.final_signal] : ''"
                >
                  {{ comp.real_signal ? comp.real_signal.final_signal : "n/d" }}
                </td>
                <td v-for="modelName in MODEL_ORDER" :key="modelName" class="px-3 py-2 text-center">
                  <template v-for="model in comp.models.filter((m) => m.model_name === modelName)" :key="model.model_name">
                    <span
                      v-if="model.predicted_direction"
                      class="px-2 py-0.5 rounded-full text-xs font-medium border cursor-help"
                      :class="directionClass(model.predicted_direction)"
                      :title="[DIRECTION_GLOSSARY[model.predicted_direction], model.agrees_with_real_signal === true ? AGREEMENT_GLOSSARY.true : model.agrees_with_real_signal === false ? AGREEMENT_GLOSSARY.false : ''].filter(Boolean).join(' ')"
                    >
                      {{ model.predicted_direction }}
                      <template v-if="model.agrees_with_real_signal === true"> ✓</template>
                      <template v-else-if="model.agrees_with_real_signal === false"> ✗</template>
                    </span>
                    <span v-else class="text-xs text-gray-400">
                      {{ model.model_status === "en_apprentissage" ? "apprentissage" : "n/d" }}
                    </span>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="store.portfolioComparison.errors.length" class="text-xs text-red-500 mb-4">
          <p v-for="err in store.portfolioComparison.errors" :key="err.ticker">{{ err.ticker }} : {{ err.error }}</p>
        </div>

        <p class="text-xs text-gray-400 italic">{{ store.portfolioComparison.disclaimer }}</p>
      </div>
    </div>
  </div>
</template>
