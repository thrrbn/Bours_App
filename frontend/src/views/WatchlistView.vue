<script setup>
// Dashboard des valeurs suivies (Etape 11bis/12) : ajout via autocomplete
// (jamais de saisie libre), signal moyen terme courant par actif, acces
// direct au dashboard complet de chaque actif.
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useWatchlistStore } from "../stores/watchlist";
import AssetAutocomplete from "../components/AssetAutocomplete.vue";
import { SIGNAL_LABELS, SIGNAL_COLORS } from "../utils/signalStyles";

const store = useWatchlistStore();
const router = useRouter();

onMounted(() => store.load());

async function onSelect(asset) {
  await store.addAsset(asset.id);
}

function goToAsset(assetId) {
  router.push({ name: "dashboard", params: { assetId } });
}
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <h2 class="text-xl font-semibold mb-4">Ma watchlist</h2>

    <div class="mb-6">
      <AssetAutocomplete @select="onSelect" />
    </div>

    <p v-if="store.error" class="text-sm text-red-600 mb-4">{{ store.error }}</p>
    <p v-if="store.isLoading" class="text-sm text-gray-500">Chargement...</p>

    <p v-if="!store.isLoading && !store.items.length" class="text-sm text-gray-400">
      Aucun actif suivi pour l'instant - utilise la recherche ci-dessus pour en ajouter.
    </p>

    <ul class="divide-y border rounded bg-white">
      <li
        v-for="item in store.items"
        :key="item.id"
        class="px-4 py-3 flex items-center justify-between gap-3 hover:bg-gray-50"
      >
        <div class="cursor-pointer flex-1" @click="goToAsset(item.asset.id)">
          <div class="flex items-center gap-2">
            <span class="font-medium">{{ item.asset.ticker }}</span>
            <span class="text-gray-500 text-sm">{{ item.asset.name }}</span>
          </div>
          <span class="text-xs text-gray-400">{{ item.asset.market }}</span>
        </div>

        <span
          v-if="store.signalsByAssetId[item.asset.id]"
          class="px-2 py-1 rounded-full text-xs font-medium border shrink-0"
          :class="SIGNAL_COLORS[store.signalsByAssetId[item.asset.id].final_signal] || 'bg-gray-100'"
        >
          {{ SIGNAL_LABELS[store.signalsByAssetId[item.asset.id].final_signal] || store.signalsByAssetId[item.asset.id].final_signal }}
        </span>
        <span v-else class="text-xs text-gray-400 shrink-0">Historique insuffisant</span>

        <button
          class="text-xs text-red-500 hover:underline shrink-0"
          @click="store.removeAsset(item.asset.id)"
        >
          Retirer
        </button>
      </li>
    </ul>

    <p class="text-xs text-gray-400 italic mt-4">
      Signal moyen terme affiche a titre indicatif - voir /api/v1/compliance/disclaimer.
    </p>
  </div>
</template>
