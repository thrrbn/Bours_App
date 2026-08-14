import { defineStore } from "pinia";
import apiClient from "../api/client";

// Scorecard de fiabilite par strategie de backtest (13/08/2026, voir
// backend/app/domains/backtests/service.py::get_strategy_scorecard) -
// alimente par le job hebdomadaire evaluate_strategies_job (parametres par
// defaut ET profils predefinis prudent/agressif depuis le 14/08/2026,
// positions du portefeuille virtuel) - distinct du scorecard du moteur de
// signal reel (stores/signalReliability.js) ET du backtest a la demande
// (ParamsLabPanel.vue).
export const useStrategyScorecardStore = defineStore("strategyScorecard", {
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
        const { data } = await apiClient.get("/backtests/strategy-scorecard");
        this.scorecard = data;
      } catch (err) {
        this.scorecard = null;
        this.error = "Impossible de charger le scorecard par strategie.";
      } finally {
        this.isLoading = false;
      }
    },
  },
});
