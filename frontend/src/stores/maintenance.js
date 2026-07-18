import { defineStore } from "pinia";
import apiClient from "../api/client";

// Store Pinia pour le bouton de maintenance global (App.vue) : declenche a
// la demande la meme sequence que les jobs planifies (prix -> news ->
// signaux -> consensus analystes), sans attendre les horaires cron. Utile
// juste apres avoir ajoute plusieurs actifs d'un coup (ex. seed BEL20).
export const useMaintenanceStore = defineStore("maintenance", {
  state: () => ({
    isRefreshing: false,
    lastSummary: null,
    error: null,
  }),
  actions: {
    async refreshAll() {
      this.isRefreshing = true;
      this.error = null;
      this.lastSummary = null;
      try {
        const { data } = await apiClient.post("/maintenance/refresh-all");
        this.lastSummary = data;
      } catch (err) {
        this.error = "Echec du rafraichissement global.";
      } finally {
        this.isRefreshing = false;
      }
    },
  },
});
