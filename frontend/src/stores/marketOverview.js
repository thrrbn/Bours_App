import { defineStore } from "pinia";
import apiClient from "../api/client";

// Store Pinia de la page "Marche" (indices FR/BE/Europe/US en direct + plus
// fortes hausses/baisses FR/US, voir backend/app/domains/market_overview/).
// Rafraichie automatiquement 3x/jour cote backend (7h, 12h, 17h) - `load()`
// se contente de lire le dernier instantane deja calcule, `refreshNow()`
// declenche un nouveau calcul a la demande.
export const useMarketOverviewStore = defineStore("marketOverview", {
  state: () => ({
    snapshot: null,
    isLoading: false,
    isRefreshing: false,
    error: null,
  }),
  actions: {
    async load() {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get("/market-overview");
        this.snapshot = data;
      } catch (err) {
        this.error = "Impossible de charger la page Marche.";
      } finally {
        this.isLoading = false;
      }
    },

    async refreshNow() {
      this.isRefreshing = true;
      this.error = null;
      try {
        const { data } = await apiClient.post("/market-overview/refresh");
        this.snapshot = data;
      } catch (err) {
        this.error = "Impossible d'actualiser la page Marche.";
      } finally {
        this.isRefreshing = false;
      }
    },
  },
});
