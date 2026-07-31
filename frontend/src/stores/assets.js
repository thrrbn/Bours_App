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
    // Fiche titre (fondamentaux Yahoo Finance, voir FundamentalsPanel.vue) -
    // separes du reste pour ne pas ecraser `error`/`isLoading` utilises par
    // le reste de la page actif (Dashboard) pendant leur chargement.
    fundamentals: null,
    sectorComparison: null,
    isLoadingFundamentals: false,
    fundamentalsError: null,
    // Recherche live Yahoo Finance (ajout d'un titre absent de la liste,
    // voir AssetSearchView.vue) - toujours un seul resultat a la fois.
    lookupResult: null,
    isLookingUp: false,
    lookupError: null,
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

    // -- Fiche titre (fondamentaux) ---------------------------------------

    async loadFundamentals(assetId) {
      this.isLoadingFundamentals = true;
      this.fundamentalsError = null;
      try {
        const { data } = await apiClient.get(`/assets/${assetId}/fundamentals`);
        this.fundamentals = data; // peut etre null : jamais rafraichi pour ce titre
      } catch (err) {
        this.fundamentals = null;
        this.fundamentalsError = "Impossible de charger la fiche titre.";
      } finally {
        this.isLoadingFundamentals = false;
      }
    },

    async refreshFundamentals(assetId) {
      this.isLoadingFundamentals = true;
      this.fundamentalsError = null;
      try {
        const { data } = await apiClient.post(`/assets/${assetId}/fundamentals/refresh`);
        this.fundamentals = data;
      } catch (err) {
        this.fundamentalsError = "Impossible de rafraichir la fiche titre depuis Yahoo Finance.";
      } finally {
        this.isLoadingFundamentals = false;
      }
    },

    async loadSectorComparison(assetId) {
      try {
        const { data } = await apiClient.get(`/assets/${assetId}/fundamentals/sector-comparison`);
        this.sectorComparison = data;
      } catch (err) {
        this.sectorComparison = null;
      }
    },

    // -- Recherche live Yahoo Finance (ajout d'un titre absent) -----------

    async lookupTicker(ticker) {
      const normalized = ticker.trim();
      if (!normalized) {
        this.lookupResult = null;
        return null;
      }
      this.isLookingUp = true;
      this.lookupError = null;
      this.lookupResult = null;
      try {
        const { data } = await apiClient.get("/assets/lookup", { params: { ticker: normalized } });
        this.lookupResult = data;
        return data;
      } catch (err) {
        this.lookupError =
          err?.response?.status === 502
            ? "Ticker introuvable sur Yahoo Finance - verifie l'orthographe ou le suffixe de place (.PA, .BR, .DE, .AS...)."
            : "Impossible de rechercher ce ticker pour le moment.";
        return null;
      } finally {
        this.isLookingUp = false;
      }
    },

    async addAssetFromLookup(lookup) {
      const { data } = await apiClient.post("/assets", {
        ticker: lookup.ticker,
        name: lookup.name || lookup.ticker,
        market: lookup.market_guess,
        sector: lookup.sector,
        currency: lookup.currency || "USD",
      });
      return data;
    },

    clearLookup() {
      this.lookupResult = null;
      this.lookupError = null;
    },

    // -- Suppression (desactivation) d'un actif ----------------------------

    async deleteAsset(assetId) {
      this.error = null;
      try {
        await apiClient.delete(`/assets/${assetId}`);
        this.allAssets = this.allAssets.filter((a) => a.id !== assetId);
        this.searchResults = this.searchResults.filter((a) => a.id !== assetId);
        return true;
      } catch (err) {
        this.error =
          err?.response?.status === 409
            ? err.response.data?.detail || "Ce titre est encore detenu en portefeuille virtuel - vends la position d'abord."
            : "Impossible de retirer ce titre.";
        return false;
      }
    },
  },
});
