import { createRouter, createWebHistory } from "vue-router";
import AssetSearchView from "../views/AssetSearchView.vue";
import DashboardView from "../views/DashboardView.vue";
import SignalHistoryView from "../views/SignalHistoryView.vue";
import WatchlistView from "../views/WatchlistView.vue";
import PortfolioView from "../views/PortfolioView.vue";
import TopBuysView from "../views/TopBuysView.vue";
import AssetStatusView from "../views/AssetStatusView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "search", component: AssetSearchView },
    { path: "/assets/:assetId", name: "dashboard", component: DashboardView, props: true },
    { path: "/history", name: "history", component: SignalHistoryView },
    { path: "/watchlist", name: "watchlist", component: WatchlistView },
    { path: "/portfolio", name: "portfolio", component: PortfolioView },
    { path: "/top-buys", name: "top-buys", component: TopBuysView },
    { path: "/status", name: "status", component: AssetStatusView },
  ],
});

export default router;
