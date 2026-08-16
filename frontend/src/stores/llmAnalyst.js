import { defineStore } from "pinia";
import apiClient from "../api/client";

// Store Pinia de l'analyste IA (16/08/2026, voir docs/20-instance-locale-pc-mac.md)
// - feature reservee a une instance locale PC/Mac avec Ollama, jamais active
// sur le NAS deploye. `status.enabled` vient du backend a l'execution (pas
// d'un flag de build cote frontend) : le meme frontend compile peut pointer
// vers une instance NAS (enabled=false, aucun lien de nav affiche) ou une
// instance locale (enabled=true) - voir App.vue.
export const useLlmAnalystStore = defineStore("llmAnalyst", {
  state: () => ({
    status: null, // { enabled, ollama_model } - null tant que non charge
    strategies: [],
    job: null,
    error: null,
    isLoadingStatus: false,
    isStarting: false,
  }),
  actions: {
    async loadStatus() {
      this.isLoadingStatus = true;
      try {
        const { data } = await apiClient.get("/llm-analyst/status");
        this.status = data;
      } catch (err) {
        // Endpoint indisponible (backend trop ancien, ou hors ligne) - traite
        // comme "desactive", jamais comme une erreur bloquante pour le reste
        // de l'app (voir App.vue : le lien de nav reste simplement masque).
        this.status = { enabled: false, ollama_model: null };
      } finally {
        this.isLoadingStatus = false;
      }
    },
    async loadStrategies() {
      if (this.strategies.length) return;
      try {
        const { data } = await apiClient.get("/llm-analyst/strategies");
        this.strategies = data;
      } catch (err) {
        this.strategies = [];
      }
    },
    async startAnalysis(assetId, strategyName, periodStart, periodEnd, modelName) {
      this.error = null;
      this.isStarting = true;
      try {
        const { data } = await apiClient.post("/llm-analyst/analyze", {
          asset_id: assetId,
          strategy_name: strategyName,
          period_start: periodStart,
          period_end: periodEnd,
          model_name: modelName || null,
        });
        this.job = data;
        return data;
      } catch (err) {
        this.error =
          err.response?.data?.detail ||
          "Impossible de lancer l'analyse - verifie qu'Ollama tourne bien en local (voir docs/20-instance-locale-pc-mac.md).";
        return null;
      } finally {
        this.isStarting = false;
      }
    },
    async pollJob(jobId) {
      try {
        const { data } = await apiClient.get(`/llm-analyst/jobs/${jobId}`);
        this.job = data;
        return data;
      } catch (err) {
        return null;
      }
    },
    reset() {
      this.job = null;
      this.error = null;
    },
  },
});
