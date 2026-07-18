import { defineStore } from "pinia";
import apiClient from "../api/client";

// Store Pinia du portefeuille virtuel de simulation (Etape 12). Aucun ordre
// reel n'est jamais passe - achats/ventes executes au dernier cours connu
// cote backend (voir backend/app/domains/portfolio/service.py).
export const usePortfolioStore = defineStore("portfolio", {
  state: () => ({
    summary: null,
    transactions: [],
    isLoading: false,
    error: null,
    actionError: null,
  }),
  actions: {
    async loadSummary() {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get("/portfolio");
        this.summary = data;
      } catch (err) {
        this.error = "Impossible de charger le portefeuille.";
      } finally {
        this.isLoading = false;
      }
    },
    async loadTransactions() {
      try {
        const { data } = await apiClient.get("/portfolio/transactions");
        this.transactions = data;
      } catch (err) {
        // non bloquant pour l'affichage du portefeuille
      }
    },
    async buy(assetId, quantity) {
      this.actionError = null;
      try {
        await apiClient.post("/portfolio/buy", { asset_id: assetId, quantity });
        await Promise.all([this.loadSummary(), this.loadTransactions()]);
        return true;
      } catch (err) {
        this.actionError = err.response?.data?.detail || "Achat impossible.";
        return false;
      }
    },
    async sell(assetId, quantity) {
      this.actionError = null;
      try {
        await apiClient.post("/portfolio/sell", { asset_id: assetId, quantity });
        await Promise.all([this.loadSummary(), this.loadTransactions()]);
        return true;
      } catch (err) {
        this.actionError = err.response?.data?.detail || "Vente impossible.";
        return false;
      }
    },
    async reset() {
      this.error = null;
      try {
        const { data } = await apiClient.post("/portfolio/reset");
        this.summary = data;
        await this.loadTransactions();
      } catch (err) {
        this.error = "Impossible de reinitialiser le portefeuille.";
      }
    },
  },
});
