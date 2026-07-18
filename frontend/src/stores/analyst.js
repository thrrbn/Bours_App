import { defineStore } from "pinia";
import apiClient from "../api/client";

// Store Pinia du domaine analyst (Etape 15) : consensus d'analystes externes
// (Yahoo Finance), jamais notre propre recommandation - toujours affiche
// avec sa source et compare, jamais fusionne, a nos propres signaux.
export const useAnalystStore = defineStore("analyst", {
  state: () => ({
    topBuys: [],
    portfolioAlerts: [],
    comparison: null,
    comparisonTable: [],
    isLoading: false,
    error: null,
  }),
  actions: {
    async loadComparisonTable(horizon = "medium") {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get("/analyst/comparison-table", { params: { horizon } });
        this.comparisonTable = data;
      } catch (err) {
        this.error = "Impossible de charger le tableau de comparaison.";
      } finally {
        this.isLoading = false;
      }
    },
    async loadTopBuys(limit = 10) {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get("/analyst/top-buys", { params: { limit } });
        this.topBuys = data;
      } catch (err) {
        this.error = "Impossible de charger le top des achats.";
      } finally {
        this.isLoading = false;
      }
    },
    async loadPortfolioAlerts() {
      try {
        const { data } = await apiClient.get("/analyst/portfolio-alerts");
        this.portfolioAlerts = data;
      } catch (err) {
        // non bloquant
      }
    },
    async loadComparison(assetId, horizon = "medium") {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get(`/analyst/${assetId}/comparison`, { params: { horizon } });
        this.comparison = data;
      } catch (err) {
        this.error = "Impossible de charger la comparaison.";
      } finally {
        this.isLoading = false;
      }
    },
    async refreshConsensus(assetId) {
      try {
        await apiClient.post(`/analyst/${assetId}/refresh`);
        return true;
      } catch (err) {
        this.error = "Impossible de rafraichir le consensus analystes.";
        return false;
      }
    },
    async refreshAll() {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.post("/analyst/refresh-all");
        return data;
      } catch (err) {
        this.error = "Impossible de rafraichir le consensus pour tous les actifs.";
        return null;
      } finally {
        this.isLoading = false;
      }
    },
  },
});
