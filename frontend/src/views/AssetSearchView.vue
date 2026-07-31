<script setup>
// Vue recherche : affiche par defaut la liste complete des actifs deja en
// base (GET /api/v1/assets), et bascule sur les resultats de recherche
// (/api/v1/assets/search) des que l'utilisateur tape une requete. Pour
// rafraichir prix/news/signaux/consensus de tous les actifs d'un coup, voir
// le bouton "Tout rafraichir maintenant" dans l'en-tete (App.vue).
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAssetsStore } from "../stores/assets";
import { fmtMarketCap } from "../constants/fundamentalsGlossary";

const query = ref("");
const store = useAssetsStore();
const router = useRouter();
const isAdding = ref(false);
const deletingId = ref(null);

onMounted(() => store.loadAll());

async function onSearch() {
  store.clearLookup();
  await store.search(query.value);
}

const displayList = computed(() => (query.value.trim() ? store.searchResults : store.allAssets));

// Rien trouve parmi les actifs deja suivis : on propose la recherche live
// Yahoo Finance (voir GET /assets/lookup) - c'est le flux "ajouter un titre
// absent de la liste".
const noLocalMatch = computed(
  () => query.value.trim() && !store.isLoading && !displayList.value.length
);

function goToAsset(asset) {
  router.push({ name: "dashboard", params: { assetId: asset.id } });
}

async function onLookup() {
  await store.lookupTicker(query.value);
}

async function onAdd() {
  if (!store.lookupResult) return;
  isAdding.value = true;
  try {
    const asset = await store.addAssetFromLookup(store.lookupResult);
    store.clearLookup();
    goToAsset(asset);
  } finally {
    isAdding.value = false;
  }
}

// Retrait (desactivation cote backend, l'historique n'est jamais efface -
// voir assets/service.py::delete_asset) - pour alleger la liste et le
// travail des jobs planifies sur des titres qui n'interessent plus.
async function onDelete(asset) {
  if (!confirm(`Retirer ${asset.ticker} (${asset.name}) de la liste ?\n\nSon historique est conserve, tu pourras le rajouter plus tard en le recherchant a nouveau sur Yahoo Finance.`)) {
    return;
  }
  deletingId.value = asset.id;
  try {
    await store.deleteAsset(asset.id);
  } finally {
    deletingId.value = null;
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <h2 class="text-xl font-semibold mb-4">Rechercher un actif</h2>
    <div class="flex gap-2 mb-2">
      <input
        v-model="query"
        type="text"
        placeholder="Ticker ou nom (ex: SOLB.BR, Solvay)"
        class="flex-1 border rounded px-3 py-2 text-sm"
        @keyup.enter="onSearch"
        @input="onSearch"
      />
      <button class="px-4 py-2 bg-gray-900 text-white rounded text-sm" @click="onSearch">Rechercher</button>
    </div>

    <p v-if="store.error" class="text-sm text-red-600 mb-4">{{ store.error }}</p>
    <p v-if="store.isLoading" class="text-sm text-gray-500 mb-4">Chargement...</p>

    <p v-if="!query.trim()" class="text-xs text-gray-400 mb-2">
      Tous les actifs deja en base ({{ store.allAssets.length }}) - tape pour filtrer.
    </p>

    <p v-if="!store.isLoading && !displayList.length && !query.trim()" class="text-sm text-gray-400">
      Aucun actif trouve.
    </p>

    <ul class="divide-y border rounded bg-white">
      <li
        v-for="asset in displayList"
        :key="asset.id"
        class="px-4 py-3 hover:bg-gray-50 cursor-pointer flex items-center justify-between gap-2"
        @click="goToAsset(asset)"
      >
        <span class="font-medium">{{ asset.ticker }}</span>
        <span class="text-gray-500 flex-1">{{ asset.name }}</span>
        <span class="text-xs text-gray-400">{{ asset.sector || asset.market }}</span>
        <button
          class="text-xs text-gray-400 hover:text-red-600 disabled:opacity-40"
          :disabled="deletingId === asset.id"
          title="Retirer ce titre de la liste (l'historique est conserve)"
          @click.stop="onDelete(asset)"
        >
          {{ deletingId === asset.id ? "..." : "Retirer" }}
        </button>
      </li>
    </ul>

    <!-- Titre absent de la liste : recherche live sur Yahoo Finance -->
    <div v-if="noLocalMatch" class="border rounded-lg p-4 bg-white mt-4">
      <p class="text-sm text-gray-600 mb-1">
        Aucun titre suivi ne correspond a « {{ query.trim() }} ».
      </p>
      <p class="text-xs text-gray-400 mb-3">
        Cherche directement sur Yahoo Finance avec le TICKER exact (pas juste le nom de l'entreprise) - ex.
        <code class="text-gray-500">AAPL</code>, <code class="text-gray-500">MC.PA</code>,
        <code class="text-gray-500">SOLB.BR</code>.
      </p>
      <button
        class="px-3 py-1.5 bg-gray-900 text-white rounded text-xs disabled:opacity-40"
        :disabled="store.isLookingUp"
        @click="onLookup"
      >
        {{ store.isLookingUp ? "Recherche..." : `Chercher "${query.trim()}" sur Yahoo Finance` }}
      </button>

      <p v-if="store.lookupError" class="text-sm text-red-600 mt-3">{{ store.lookupError }}</p>

      <div v-if="store.lookupResult" class="border rounded-lg p-3 bg-gray-50 mt-3">
        <div class="flex items-center justify-between mb-1">
          <span class="font-medium text-sm">{{ store.lookupResult.ticker }}</span>
          <span class="text-xs text-gray-400">{{ store.lookupResult.market_guess }}</span>
        </div>
        <p class="text-sm text-gray-600 mb-2">{{ store.lookupResult.name || "Nom indisponible" }}</p>
        <div class="flex flex-wrap gap-3 text-xs text-gray-500 mb-3">
          <span v-if="store.lookupResult.sector">Secteur : {{ store.lookupResult.sector }}</span>
          <span v-if="store.lookupResult.last_price !== null">
            Dernier cours : {{ store.lookupResult.last_price.toFixed(2) }} {{ store.lookupResult.currency || "" }}
          </span>
          <span v-if="store.lookupResult.market_cap !== null">
            Capitalisation : {{ fmtMarketCap(store.lookupResult.market_cap) }}
          </span>
        </div>

        <button
          v-if="store.lookupResult.already_tracked_id"
          class="px-3 py-1.5 bg-gray-200 text-gray-700 rounded text-xs"
          @click="goToAsset({ id: store.lookupResult.already_tracked_id })"
        >
          Deja suivi - voir la fiche
        </button>
        <button
          v-else
          class="px-3 py-1.5 bg-emerald-600 text-white rounded text-xs disabled:opacity-40"
          :disabled="isAdding"
          @click="onAdd"
        >
          {{ isAdding ? "Ajout..." : "Ajouter ce titre" }}
        </button>
      </div>
    </div>
  </div>
</template>
