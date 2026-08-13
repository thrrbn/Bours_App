import { defineStore } from "pinia";
import apiClient from "../api/client";

// Store Pinia du bac a sable pedagogique "analysis_lab" (31/07/2026, voir
// docs/STACK.md) : lecture seule, aucune ecriture cote backend. Trois vues
// possibles sur un meme actif - la derniere valeur des indicateurs
// techniques, la comparaison des modeles legers (Random Forest/XGBoost/
// ARIMA) au signal reel, et la meme comparaison sur tout le portefeuille
// virtuel (reutilise les actifs deja suivis en simulation, demande explicite
// de l'utilisateur plutot qu'un univers de test separe).
export const useAnalysisLabStore = defineStore("analysisLab", {
  state: () => ({
    featureSnapshot: null,
    comparison: null,
    portfolioComparison: null,
    isLoadingFeatures: false,
    isLoadingComparison: false,
    isLoadingPortfolio: false,
    error: null,
    // Phase 3 (31/07/2026) : LSTM entraine de maniere ASYNCHRONE (voir
    // jobs/deep_training_job.py) - trop long pour un appel synchrone comme
    // /compare. `deepJob` reflete le dernier statut connu (pending/running/
    // completed/failed), rafraichi par polling depuis la vue.
    deepJob: null,
    // Laboratoire d'indicateurs (13/08/2026, voir backend/.../feature_engineering.py::
    // ADJUSTABLE_INDICATORS) : `adjustableIndicators` est charge UNE fois
    // (registre statique cote backend, ne depend pas de l'actif selectionne)
    // et mis en cache ici - `recomputeResult` est le dernier recalcul demande.
    adjustableIndicators: [],
    recomputeResult: null,
    isRecomputing: false,
    recomputeError: null,
  }),
  actions: {
    async loadAdjustableIndicators() {
      if (this.adjustableIndicators.length) return; // deja charge, registre statique
      try {
        const { data } = await apiClient.get("/analysis-lab/indicators/adjustable");
        this.adjustableIndicators = data;
      } catch (err) {
        this.adjustableIndicators = [];
      }
    },
    async recomputeIndicator(assetId, indicatorKey, params) {
      this.isRecomputing = true;
      this.recomputeError = null;
      try {
        const { data } = await apiClient.post(`/analysis-lab/${assetId}/indicators/${indicatorKey}/recompute`, {
          params,
        });
        this.recomputeResult = data;
      } catch (err) {
        this.recomputeResult = null;
        this.recomputeError = "Impossible de recalculer cet indicateur (historique de prix insuffisant ?).";
      } finally {
        this.isRecomputing = false;
      }
    },
    async loadFeatureSnapshot(assetId) {
      this.isLoadingFeatures = true;
      this.error = null;
      try {
        const { data } = await apiClient.get(`/analysis-lab/${assetId}/features`);
        this.featureSnapshot = data;
      } catch (err) {
        this.featureSnapshot = null;
        this.error =
          err?.response?.status === 404
            ? "Historique de prix insuffisant pour cet actif - rafraichis d'abord ses prix."
            : "Impossible de charger les indicateurs techniques.";
      } finally {
        this.isLoadingFeatures = false;
      }
    },
    async loadComparison(assetId, horizon = "medium") {
      this.isLoadingComparison = true;
      this.error = null;
      try {
        const { data } = await apiClient.get(`/analysis-lab/${assetId}/compare`, { params: { horizon } });
        this.comparison = data;
      } catch (err) {
        this.comparison = null;
        this.error = "Impossible de comparer les modeles au signal reel pour cet actif.";
      } finally {
        this.isLoadingComparison = false;
      }
    },
    async loadPortfolioComparison(horizon = "medium") {
      this.isLoadingPortfolio = true;
      this.error = null;
      try {
        const { data } = await apiClient.get("/analysis-lab/portfolio-compare", { params: { horizon } });
        this.portfolioComparison = data;
      } catch (err) {
        this.portfolioComparison = null;
        this.error = "Impossible de charger la comparaison sur le portefeuille.";
      } finally {
        this.isLoadingPortfolio = false;
      }
    },
    async startDeepTraining(assetId, modelName = "lstm", horizon = "medium") {
      this.error = null;
      try {
        const { data } = await apiClient.post(`/analysis-lab/${assetId}/train-deep`, {
          model_name: modelName,
          horizon,
        });
        this.deepJob = data;
        return data;
      } catch (err) {
        this.error = "Impossible de lancer l'entrainement asynchrone (LSTM).";
        return null;
      }
    },
    async pollDeepJob(jobId) {
      try {
        const { data } = await apiClient.get(`/analysis-lab/training-jobs/${jobId}`);
        this.deepJob = data;
        return data;
      } catch (err) {
        return null;
      }
    },
    reset() {
      this.featureSnapshot = null;
      this.comparison = null;
      this.deepJob = null;
      this.recomputeResult = null;
      this.recomputeError = null;
    },
  },
});
