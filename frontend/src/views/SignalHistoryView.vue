<script setup>
// Historique des signaux d'un actif - selection via autocomplete (jamais de
// saisie d'UUID a la main, meme piege que l'ancienne recherche d'actifs,
// voir AssetAutocomplete.vue).
import { ref, watch } from "vue";
import { useSignalsStore } from "../stores/signals";
import AssetAutocomplete from "../components/AssetAutocomplete.vue";
import TrendChart from "../components/TrendChart.vue";
import HorizonTabs from "../components/HorizonTabs.vue";

const selectedAsset = ref(null);
const activeHorizon = ref("short");
const store = useSignalsStore();

async function loadHistory() {
  if (!selectedAsset.value) return;
  await store.loadHistory(selectedAsset.value.id, activeHorizon.value);
}

function onSelectAsset(asset) {
  selectedAsset.value = asset;
  loadHistory();
}

watch(activeHorizon, loadHistory);
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <h2 class="text-xl font-semibold mb-4">Historique des signaux</h2>

    <div class="mb-4">
      <AssetAutocomplete @select="onSelectAsset" />
      <p v-if="selectedAsset" class="text-xs text-gray-500 mt-1">
        Actif selectionne : {{ selectedAsset.ticker }} - {{ selectedAsset.name }}
      </p>
    </div>

    <HorizonTabs v-model="activeHorizon" />

    <p v-if="store.error" class="text-sm text-red-600 mb-4">{{ store.error }}</p>
    <p v-if="store.isLoading" class="text-sm text-gray-500 mb-2">Chargement...</p>

    <div class="bg-white border rounded p-4">
      <p v-if="!selectedAsset" class="text-sm text-gray-400">Choisis un actif ci-dessus pour voir son historique.</p>
      <TrendChart v-else :history="store.history" />
    </div>
  </div>
</template>
