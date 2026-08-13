import { defineStore } from "pinia";
import apiClient from "../api/client";

// Scorecard de fiabilite reelle des signaux (13/08/2026, voir
// backend/app/domains/signal_reliability/) - distinct du labo de backtest
// (ParamsLabPanel.vue, a la demande) : precision du moteur de signal REEL,
// alimentee automatiquement par un job quotidien, jamais recalculee a la
// volee ici.
export const useSignalReliabilityStore = defineStore("signalReliability", {
  state: () => ({
    scorecard: null,
    isLoading: false,
    error: null,
  }),
  actions: {
    async load() {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get("/signal-reliability/scorecard");
        this.scorecard = data;
      } catch (err) {
        this.scorecard = null;
        this.error = "Impossible de charger le scorecard de fiabilite.";
      } finally {
        this.isLoading = false;
      }
    },
  },
});
