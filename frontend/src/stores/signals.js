import { defineStore } from "pinia";
import apiClient from "../api/client";

const HORIZONS = ["short", "medium", "long"];

// Store Pinia du domaine signals - un signal par horizon, jamais affiche sans
// ses explications (le backend garantit deja cette contrainte via son schema
// Pydantic, voir docs/07-endpoints-fastapi.md).
export const useSignalsStore = defineStore("signals", {
  state: () => ({
    signalsByHorizon: {},
    history: [],
    isLoading: false,
    error: null,
  }),
  actions: {
    async loadSignal(assetId, horizon = "short") {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get(`/signals/${assetId}`, { params: { horizon } });
        this.signalsByHorizon = { ...this.signalsByHorizon, [horizon]: data };
      } catch (err) {
        this.error = "Impossible de calculer le signal pour cet actif (historique insuffisant ?).";
      } finally {
        this.isLoading = false;
      }
    },
    async loadAllHorizons(assetId) {
      await Promise.all(HORIZONS.map((h) => this.loadSignal(assetId, h)));
    },
    async loadHistory(assetId, horizon = "short") {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get(`/signals/${assetId}/history`, { params: { horizon } });
        this.history = data;
      } catch (err) {
        this.error = "Impossible de charger l'historique des signaux.";
      } finally {
        this.isLoading = false;
      }
    },
  },
});
