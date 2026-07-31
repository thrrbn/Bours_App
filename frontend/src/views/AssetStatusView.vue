<script setup>
// Suivi des actifs (30/07/2026) : montre la fraicheur des donnees (prix,
// signal, consensus analystes) titre par titre, avec une progression
// visible pendant un rafraichissement global - plutot que le bouton "Tout
// rafraichir maintenant" existant (App.vue) qui tourne plusieurs minutes
// sans aucun retour intermediaire. Reutilise uniquement des endpoints par
// actif deja existants (voir stores/assetStatus.js), aucune nouvelle
// infrastructure de job/streaming cote backend.
import { onMounted } from "vue";
import { useAssetStatusStore } from "../stores/assetStatus";

const store = useAssetStatusStore();

onMounted(() => store.loadStatus());

function fmtDate(value) {
  if (!value) return "jamais";
  return new Date(value).toLocaleString("fr-BE", { dateStyle: "medium", timeStyle: "short" });
}

function fmtDay(value) {
  if (!value) return "jamais";
  return new Date(value).toLocaleDateString("fr-BE", { dateStyle: "medium" });
}

function isStale(value, maxDays) {
  if (!value) return true;
  const ageMs = Date.now() - new Date(value).getTime();
  return ageMs > maxDays * 24 * 60 * 60 * 1000;
}
</script>

<template>
  <div class="max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-1">
      <h2 class="text-xl font-semibold">Suivi des actifs</h2>
      <button
        class="text-xs border rounded px-3 py-1.5 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
        :disabled="store.isRefreshingAll || !store.rows.length"
        @click="store.refreshAllSequential"
      >
        {{ store.isRefreshingAll ? "Rafraichissement en cours..." : "Rafraichir tout (titre par titre)" }}
      </button>
    </div>
    <p class="text-xs text-gray-400 mb-3">
      Prix, signal et consensus analystes par titre, mis a jour un par un - force la mise a jour d'un titre precis
      avec le bouton de sa ligne, ou enchaine tous les titres avec le bouton ci-dessus.
    </p>

    <div v-if="store.isRefreshingAll" class="bg-blue-50 border border-blue-200 text-blue-800 text-sm rounded px-3 py-2 mb-3">
      Traitement {{ store.currentIndex }}/{{ store.total }} - <span class="font-medium">{{ store.currentTicker }}</span> en cours...
      <div class="h-1.5 bg-blue-100 rounded-full overflow-hidden mt-1">
        <div
          class="h-1.5 bg-blue-500 transition-all"
          :style="{ width: (store.total ? (store.currentIndex / store.total) * 100 : 0) + '%' }"
        ></div>
      </div>
    </div>

    <p v-if="store.error" class="text-sm text-red-600 mb-4">{{ store.error }}</p>
    <p v-if="store.isLoading" class="text-sm text-gray-500">Chargement...</p>
    <p v-if="!store.isLoading && !store.rows.length" class="text-sm text-gray-400">
      Aucun actif suivi - ajoute des titres via la recherche ou les endpoints de seed (voir docs/STACK.md).
    </p>

    <div v-if="store.rows.length" class="border rounded bg-white overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
          <tr>
            <th class="text-left px-3 py-2">Actif</th>
            <th class="text-left px-3 py-2">Derniers prix</th>
            <th class="text-left px-3 py-2">Dernier signal</th>
            <th class="text-left px-3 py-2">Dernier consensus</th>
            <th class="text-right px-3 py-2">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y">
          <tr v-for="row in store.rows" :key="row.id" class="hover:bg-gray-50">
            <td class="px-3 py-2">
              <span class="font-medium">{{ row.ticker }}</span>
              <span class="text-gray-500 text-xs block">{{ row.name }} · {{ row.market }}</span>
            </td>
            <td class="px-3 py-2" :class="isStale(row.last_price_date, 3) ? 'text-amber-600' : 'text-gray-700'">
              {{ fmtDay(row.last_price_date) }}
            </td>
            <td class="px-3 py-2" :class="isStale(row.last_signal_computed_at, 3) ? 'text-amber-600' : 'text-gray-700'">
              {{ fmtDate(row.last_signal_computed_at) }}
            </td>
            <td class="px-3 py-2" :class="isStale(row.last_consensus_fetched_at, 14) ? 'text-amber-600' : 'text-gray-700'">
              {{ fmtDate(row.last_consensus_fetched_at) }}
            </td>
            <td class="px-3 py-2 text-right">
              <button
                class="text-xs border rounded px-2 py-1 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                :disabled="store.refreshingRowId === row.id || store.isRefreshingAll"
                @click="store.refreshRow(row)"
              >
                {{ store.refreshingRowId === row.id ? "..." : "Forcer la mise a jour" }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="text-xs text-gray-400 italic mt-4">
      "jamais" = donnee pas encore calculee pour ce titre (frequent juste apres un ajout - lance un rafraichissement).
      En orange : donnee de plus de 3 jours (prix/signal) ou 14 jours (consensus analystes) - purement indicatif, pas
      une alerte de conformite.
    </p>
  </div>
</template>
