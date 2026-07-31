import { defineStore } from "pinia";
import apiClient from "../api/client";

// Store Pinia de la page "Suivi des actifs" : montre pour chaque titre suivi
// la fraicheur des donnees (prix / signal / consensus analystes) et permet
// de forcer une mise a jour titre par titre, avec une progression visible -
// plutot qu'un seul gros bouton "tout rafraichir" qui tourne en boucle sans
// retour (voir maintenance.js pour ce bouton global existant). Reutilise
// exclusivement des endpoints par actif deja existants : POST
// /market-data/{id}/refresh, /signals/{id}/recompute, /analyst/{id}/refresh.
// Aucun nouvel endpoint de rafraichissement cote backend, uniquement une
// boucle sequentielle cote client - simple et robuste (voir docs/STACK.md).
const HORIZONS = ["short", "medium", "long"];

export const useAssetStatusStore = defineStore("assetStatus", {
  state: () => ({
    rows: [],
    isLoading: false,
    error: null,
    isRefreshingAll: false,
    currentIndex: 0,
    currentTicker: null,
    refreshingRowId: null,
  }),
  getters: {
    total: (state) => state.rows.length,
  },
  actions: {
    async loadStatus() {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get("/assets/status");
        this.rows = data;
      } catch (err) {
        this.error = "Impossible de charger le suivi des actifs.";
      } finally {
        this.isLoading = false;
      }
    },

    // Rafraichit un seul titre : prix -> signal (3 horizons) -> consensus
    // analystes, dans cet ordre (le signal a besoin des prix a jour, la
    // comparaison avec le consensus n'en a pas besoin mais autant tout
    // regrouper en une seule action "forcer la mise a jour de ce titre").
    async refreshRow(row) {
      this.refreshingRowId = row.id;
      try {
        try {
          const { data } = await apiClient.post(`/market-data/${row.id}/refresh`);
          if (data.latest_trade_date) row.last_price_date = data.latest_trade_date;
        } catch (err) {
          // non bloquant : on tente quand meme signal/analyste avec les prix existants
        }

        for (const horizon of HORIZONS) {
          try {
            const { data } = await apiClient.post(`/signals/${row.id}/recompute`, null, { params: { horizon } });
            if (data.computed_at) row.last_signal_computed_at = data.computed_at;
          } catch (err) {
            // frequent : historique de prix encore insuffisant pour ce titre - pas une panne globale
          }
        }

        try {
          const { data } = await apiClient.post(`/analyst/${row.id}/refresh`);
          if (data && data.fetched_at) row.last_consensus_fetched_at = data.fetched_at;
        } catch (err) {
          // frequent : pas de couverture analystes pour ce titre - pas une panne globale
        }
      } finally {
        this.refreshingRowId = null;
      }
    },

    // Enchaine refreshRow() sur tous les titres, un par un, en exposant la
    // progression (currentIndex/total/currentTicker) pour que l'interface
    // montre concretement "quel titre est en cours de traitement" plutot
    // qu'un spinner opaque pendant plusieurs minutes.
    async refreshAllSequential() {
      this.isRefreshingAll = true;
      this.currentIndex = 0;
      try {
        for (const row of this.rows) {
          this.currentIndex += 1;
          this.currentTicker = row.ticker;
          await this.refreshRow(row);
        }
      } finally {
        this.isRefreshingAll = false;
        this.currentTicker = null;
      }
    },
  },
});
