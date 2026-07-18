<script setup>
// Vue recherche : affiche par defaut la liste complete des actifs deja en
// base (GET /api/v1/assets), et bascule sur les resultats de recherche
// (/api/v1/assets/search) des que l'utilisateur tape une requete. Pour
// rafraichir prix/news/signaux/consensus de tous les actifs d'un coup, voir
// le bouton "Tout rafraichir maintenant" dans l'en-tete (App.vue).
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAssetsStore } from "../stores/assets";

const query = ref("");
const store = useAssetsStore();
const router = useRouter();

onMounted(() => store.loadAll());

async function onSearch() {
  await store.search(query.value);
}

const displayList = computed(() => (query.value.trim() ? store.searchResults : store.allAssets));

function goToAsset(asset) {
  router.push({ name: "dashboard", params: { assetId: asset.id } });
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

    <p v-if="!store.isLoading && !displayList.length" class="text-sm text-gray-400">
      Aucun actif trouve.
    </p>

    <ul class="divide-y border rounded bg-white">
      <li
        v-for="asset in displayList"
        :key="asset.id"
        class="px-4 py-3 hover:bg-gray-50 cursor-pointer flex justify-between"
        @click="goToAsset(asset)"
      >
        <span class="font-medium">{{ asset.ticker }}</span>
        <span class="text-gray-500">{{ asset.name }}</span>
        <span class="text-xs text-gray-400">{{ asset.sector || asset.market }}</span>
      </li>
    </ul>
  </div>
</template>
