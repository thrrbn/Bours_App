// Libelles et couleurs partages entre SignalCard.vue et le dashboard watchlist
// (WatchlistView.vue) - un seul endroit a modifier si le vocabulaire des
// signaux change (voir docs/11-strategie-scoring-hybride.md).
export const SIGNAL_LABELS = {
  achat_speculatif: "Achat speculatif",
  surveillance: "Surveillance",
  neutre: "Neutre",
  prudence: "Prudence",
  vente_defensive: "Vente defensive",
};

export const SIGNAL_COLORS = {
  achat_speculatif: "bg-achat/10 text-achat border-achat/30",
  surveillance: "bg-surveillance/10 text-surveillance border-surveillance/30",
  neutre: "bg-neutre/10 text-neutre border-neutre/30",
  prudence: "bg-prudence/10 text-prudence border-prudence/30",
  vente_defensive: "bg-vente/10 text-vente border-vente/30",
};

// Statut de maturite du modele statistique V2 (docs/11)
export const ML_STATUS_STYLES = {
  en_apprentissage: "bg-amber-50 text-amber-700 border-amber-300",
  fiable: "bg-emerald-50 text-emerald-700 border-emerald-300",
};

export const ML_STATUS_LABELS = {
  en_apprentissage: "En apprentissage",
  fiable: "Fiable",
};
