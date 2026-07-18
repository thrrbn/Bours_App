<script setup>
// Champ de recherche avec suggestions - remplace toute saisie libre de
// ticker/ISIN par une selection dans une liste d'actifs reels (s'appuie sur
// /api/v1/assets/search, deja utilise par AssetSearchView.vue). Emet
// "select" avec l'objet actif complet ; ne laisse jamais valider un texte
// libre qui ne correspond a aucun actif connu.
import { ref } from "vue";
import apiClient from "../api/client";

const emit = defineEmits(["select"]);

const query = ref("");
const suggestions = ref([]);
const isOpen = ref(false);
const isLoading = ref(false);
let debounceTimer = null;

function onInput() {
  clearTimeout(debounceTimer);
  if (!query.value.trim()) {
    suggestions.value = [];
    isOpen.value = false;
    return;
  }
  debounceTimer = setTimeout(runSearch, 250);
}

async function runSearch() {
  isLoading.value = true;
  try {
    const { data } = await apiClient.get("/assets/search", { params: { q: query.value } });
    suggestions.value = data;
    isOpen.value = true;
  } catch (err) {
    suggestions.value = [];
  } finally {
    isLoading.value = false;
  }
}

function pick(asset) {
  emit("select", asset);
  query.value = "";
  suggestions.value = [];
  isOpen.value = false;
}

function onBlur() {
  // Laisse le temps au clic sur une suggestion de se declencher avant de fermer.
  setTimeout(() => {
    isOpen.value = false;
  }, 150);
}
</script>

<template>
  <div class="relative">
    <input
      v-model="query"
      type="text"
      placeholder="Chercher un actif a suivre (ticker ou nom)..."
      class="w-full border rounded px-3 py-2 text-sm"
      @input="onInput"
      @focus="() => suggestions.length && (isOpen = true)"
      @blur="onBlur"
    />
    <p v-if="isLoading" class="text-xs text-gray-400 mt-1">Recherche...</p>

    <ul
      v-if="isOpen && suggestions.length"
      class="absolute z-10 mt-1 w-full bg-white border rounded shadow-sm divide-y max-h-64 overflow-auto"
    >
      <li
        v-for="asset in suggestions"
        :key="asset.id"
        class="px-3 py-2 text-sm hover:bg-gray-50 cursor-pointer flex justify-between"
        @mousedown.prevent="pick(asset)"
      >
        <span class="font-medium">{{ asset.ticker }}</span>
        <span class="text-gray-500">{{ asset.name }}</span>
        <span class="text-xs text-gray-400">{{ asset.market }}</span>
      </li>
    </ul>

    <p v-if="isOpen && !suggestions.length && !isLoading" class="absolute z-10 mt-1 w-full bg-white border rounded shadow-sm px-3 py-2 text-sm text-gray-400">
      Aucun actif trouve - verifie l'orthographe ou ajoute-le d'abord via la recherche.
    </p>
  </div>
</template>
