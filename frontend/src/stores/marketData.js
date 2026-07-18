import { defineStore } from "pinia";
import apiClient from "../api/client";

// Store Pinia pour la tendance REELLE passee (1/3/6/12 mois) - jamais une
// prediction, calculee directement a partir des prix connus. Sert de point
// de comparaison honnete face aux avis d'analystes externes (Yahoo), qui
// refletent typiquement un horizon ~12 mois plus long que nos propres
// horizons de prediction (5/20/60 jours - voir docs/11).
export const useMarketDataStore = defineStore("marketData", {
  state: () => ({
    trendsByAssetId: {},
  }),
  actions: {
    async loadHistoricalTrend(assetId) {
      try {
        const { data } = await apiClient.get(`/market-data/${assetId}/historical-trend`);
        this.trendsByAssetId = { ...this.trendsByAssetId, [assetId]: data };
        return data;
      } catch (err) {
        this.trendsByAssetId = { ...this.trendsByAssetId, [assetId]: null };
        return null;
      }
    },
  },
});
