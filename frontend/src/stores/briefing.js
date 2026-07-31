import { defineStore } from "pinia";
import apiClient from "../api/client";

// Store Pinia du briefing quotidien (portefeuille virtuel + watchlist, voir
// backend/app/domains/notifications/briefing_service.py) et des mots-cles
// personnalises qui l'alimentent (domaine news).
export const useBriefingStore = defineStore("briefing", {
  state: () => ({
    briefing: null,
    isLoading: false,
    error: null,
    lastAction: null, // 'preview' | 'send' - pour distinguer l'origine du dernier `briefing` charge

    customKeywords: [],
    isLoadingKeywords: false,
    keywordsError: null,

    isRescanning: false,
    rescanResult: null,

    keywordMatches: [],
    isLoadingMatches: false,
    matchesError: null,

    keywordSummaryLines: [],
    isLoadingSummary: false,
    summaryError: null,

    // Resume par article, en cache par id (voir GET /news/articles/{id}/summary).
    articleSummaries: {},
    loadingArticleSummaryId: null,
    articleSummaryError: null,
  }),
  actions: {
    async loadPreview(windowDays = 3) {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.get("/notifications/briefing/preview", { params: { window_days: windowDays } });
        this.briefing = data;
        this.lastAction = "preview";
      } catch (err) {
        this.error = "Impossible de charger l'apercu du briefing.";
      } finally {
        this.isLoading = false;
      }
    },

    async sendNow() {
      this.isLoading = true;
      this.error = null;
      try {
        const { data } = await apiClient.post("/notifications/briefing/send");
        this.briefing = data;
        this.lastAction = "send";
      } catch (err) {
        this.error = "Impossible de declencher l'envoi du briefing.";
      } finally {
        this.isLoading = false;
      }
    },

    async loadCustomKeywords() {
      this.isLoadingKeywords = true;
      this.keywordsError = null;
      try {
        const { data } = await apiClient.get("/news/custom-keywords");
        this.customKeywords = data;
      } catch (err) {
        this.keywordsError = "Impossible de charger les mots-cles personnalises.";
      } finally {
        this.isLoadingKeywords = false;
      }
    },

    async addCustomKeyword(keyword, weight, horizonImpact) {
      this.keywordsError = null;
      try {
        await apiClient.post("/news/custom-keywords", { keyword, weight, horizon_impact: horizonImpact });
        await this.loadCustomKeywords();
        return true;
      } catch (err) {
        this.keywordsError = "Impossible d'ajouter ce mot-cle.";
        return false;
      }
    },

    async deleteCustomKeyword(id) {
      this.keywordsError = null;
      try {
        await apiClient.delete(`/news/custom-keywords/${id}`);
        this.customKeywords = this.customKeywords.filter((k) => k.id !== id);
      } catch (err) {
        this.keywordsError = "Impossible de supprimer ce mot-cle.";
      }
    },

    // Repasse les articles DEJA en base au lexique actuel (fixe + mots-cles
    // personnalises), sans reingerer - voir POST /news/rescan-keywords.
    async rescanKeywords() {
      this.isRescanning = true;
      this.keywordsError = null;
      this.rescanResult = null;
      try {
        const { data } = await apiClient.post("/news/rescan-keywords");
        this.rescanResult = data;
        return data;
      } catch (err) {
        this.keywordsError = "Impossible de rescanner les articles existants.";
        return null;
      } finally {
        this.isRescanning = false;
      }
    },

    // Articles (toutes dates, tous actifs) qui matchent un mot-cle
    // personnalise - voir GET /news/keyword-matches.
    async loadKeywordMatches(limit = 30) {
      this.isLoadingMatches = true;
      this.matchesError = null;
      try {
        const { data } = await apiClient.get("/news/keyword-matches", { params: { limit } });
        this.keywordMatches = data;
      } catch (err) {
        this.matchesError = "Impossible de charger les articles correspondants.";
      } finally {
        this.isLoadingMatches = false;
      }
    },

    // Resume en francais (une ligne par mot-cle, plafonne), voir GET
    // /news/keyword-matches/summary.
    async loadKeywordSummary(maxLines = 10) {
      this.isLoadingSummary = true;
      this.summaryError = null;
      try {
        const { data } = await apiClient.get("/news/keyword-matches/summary", { params: { max_lines: maxLines } });
        this.keywordSummaryLines = data;
      } catch (err) {
        this.summaryError = "Impossible de generer le resume.";
      } finally {
        this.isLoadingSummary = false;
      }
    },

    // Resume d'UN article precis, mis en cache par id - un second clic
    // n'appelle pas a nouveau l'API (voir toggleArticleSummary cote vue).
    async loadArticleSummary(articleId, maxLines = 10) {
      this.loadingArticleSummaryId = articleId;
      this.articleSummaryError = null;
      try {
        const { data } = await apiClient.get(`/news/articles/${articleId}/summary`, { params: { max_lines: maxLines } });
        this.articleSummaries = { ...this.articleSummaries, [articleId]: data };
      } catch (err) {
        this.articleSummaryError = "Impossible de generer le resume de cet article.";
      } finally {
        this.loadingArticleSummaryId = null;
      }
    },
  },
});
