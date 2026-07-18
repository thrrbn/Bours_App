import { defineStore } from "pinia";
import apiClient from "../api/client";

// Store Pinia du domaine assets - recherche et selection de l'actif courant.
export const useAssetsStore = defineStore("assets", {
  state: () => ({
    searchResults: [],
    allAssets: [],
    selectedAsset: null,
    isLoading: false,
    error: null,
  }),
  actions: {
    async loadAll() {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get("/assets");
        this.allAssets = data;
      } catch (err) {
        this.error = "Impossible de charger la liste des actifs.";
      } finally {
        this.isLoading = false;
      }
    },
    async search(query) {
      if (!query.trim()) {
        this.searchResults = [];
        return;
      }
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get("/assets/search", { params: { q: query } });
        this.searchResults = data;
      } catch (err) {
        this.error = "Impossible de rechercher les actifs pour le moment.";
      } finally {
        this.isLoading = false;
      }
    },
    async loadAsset(assetId) {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get(`/assets/${assetId}`);
        this.selectedAsset = data;
      } catch (err) {
        this.error = "Actif introuvable.";
      } finally {
        this.isLoading = false;
      }
    },
  },
});
