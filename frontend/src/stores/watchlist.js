import { defineStore } from "pinia";
import apiClient from "../api/client";

// Store Pinia de la watchlist (Etape 11bis) : liste des actifs suivis +
// signal courant (horizon moyen terme) pour chacun, utilise comme "dashboard
// des valeurs". L'ajout se fait toujours par asset_id (jamais de saisie
// libre de ticker), via AssetAutocomplete.vue qui s'appuie sur
// /api/v1/assets/search.
export const useWatchlistStore = defineStore("watchlist", {
  state: () => ({
    items: [],
    signalsByAssetId: {},
    isLoading: false,
    error: null,
  }),
  actions: {
    async load() {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get("/watchlist");
        this.items = data;
        await this.loadSignals();
      } catch (err) {
        this.error = "Impossible de charger la watchlist.";
      } finally {
        this.isLoading = false;
      }
    },
    async loadSignals() {
      await Promise.all(
        this.items.map(async (item) => {
          try {
            const { data } = await apiClient.get(`/signals/${item.asset.id}`, {
              params: { horizon: "medium" },
            });
            this.signalsByAssetId = { ...this.signalsByAssetId, [item.asset.id]: data };
          } catch (err) {
            // Historique insuffisant pour cet actif - pas bloquant pour le reste du dashboard.
            this.signalsByAssetId = { ...this.signalsByAssetId, [item.asset.id]: null };
          }
        })
      );
    },
    async addAsset(assetId) {
      this.error = null;
      try {
        await apiClient.post("/watchlist", { asset_id: assetId, notify_on_change: true });
        await this.load();
        return true;
      } catch (err) {
        this.error =
          err.response?.status === 409
            ? "Cet actif est deja dans la watchlist."
            : "Impossible d'ajouter cet actif a la watchlist.";
        return false;
      }
    },
    async removeAsset(assetId) {
      this.error = null;
      try {
        await apiClient.delete(`/watchlist/${assetId}`);
        this.items = this.items.filter((item) => item.asset.id !== assetId);
      } catch (err) {
        this.error = "Impossible de retirer cet actif de la watchlist.";
      }
    },
  },
});
