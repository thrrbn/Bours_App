/**
 * Glossaire pedagogique du laboratoire de parametres / backtest par titre
 * (voir backend/app/domains/backtests/kernc_engine.py, librairie
 * backtesting.py de kernc, github.com/kernc/backtesting.py). Meme objectif
 * que analysisLabGlossary.js : chaque statistique affichee doit etre
 * explicable d'un survol de souris.
 *
 * Point de vigilance specifique a ce glossaire (a la difference des
 * indicateurs techniques) : plusieurs de ces metriques ont une direction
 * "meilleur/moins bon" reconnue dans la litterature (un Sharpe de 3 est
 * objectivement plus favorable qu'un Sharpe de 0.3), contrairement a un RSI
 * qui n'a pas de "bon chiffre" universel. On explique donc cette direction
 * dans le texte - MAIS cela reste une mesure de la qualite statistique d'un
 * BACKTEST PASSE, jamais une prediction ni une recommandation sur le titre
 * lui-meme (voir docs/17-limites-legales-techniques.md). Un excellent
 * backtest ne garantit rien sur l'avenir ; un mauvais backtest sur une
 * strategie simple ne dit rien du titre en tant qu'investissement.
 */

// ---------------------------------------------------------------------------
// Strategies disponibles
// ---------------------------------------------------------------------------

export const STRATEGY_GLOSSARY = {
  internal_rules:
    "Le moteur de regles reel de l'application (voir signals/models_ml/baseline_rules.py) : compare chaque signal individuellement au rendement qui a suivi, SANS simuler de vrai cash/position (juste 'ce signal avait-il raison ?'). Complementaire de signal_replay (backtesting.py), qui simule un vrai portefeuille - les deux rejouent les MEMES signaux mais mesurent des choses differentes.",
  signal_replay:
    "Rejoue les signaux de cette application comme de vrais ordres (achat quand le signal devient haussier, vente quand il devient baissier) - la comparaison la plus directe avec ce que « suivre nos signaux » aurait vraiment produit, frais inclus.",
  sma_cross:
    "Croisement de moyennes mobiles (benchmark classique, exemple du README de backtesting.py) : achete quand la moyenne courte croise au-dessus de la longue, vend quand elle croise en dessous. Sert de point de comparaison simple et connu du secteur.",
  rsi_mean_reversion:
    "RSI - retour a la moyenne (benchmark classique) : achete quand le RSI ressort de la zone de survente (repasse au-dessus du seuil bas), vend quand il ressort de la zone de surachat (repasse en dessous du seuil haut). Periode et seuils modulables.",
  macd_cross:
    "MACD - croisement (benchmark classique) : achete quand la ligne MACD croise au-dessus de sa ligne de signal (momentum haussier naissant), vend quand elle croise en dessous. Fenetres rapide/lente/signal modulables.",
  bollinger_reversion:
    "Bandes de Bollinger - retour a la moyenne (benchmark classique) : achete au contact de la bande basse (prix statistiquement bas par rapport a sa moyenne recente), vend au contact de la bande haute. Periode et largeur des bandes modulables.",
  buy_and_hold:
    "Achete au premier jour disponible et ne revend jamais (benchmark le plus simple) - reference incontournable : une strategie active qui ne bat pas nettement ce chiffre n'apporte probablement rien une fois les frais comptes.",
};

// ---------------------------------------------------------------------------
// Metriques - cle normalisee (voir ParamsLabPanel.vue::METRIC_ROWS pour le
// mapping vers les champs bruts de l'API, qui melangent champs types
// (sharpe_ratio, win_rate...) et extra_metrics (cles brutes backtesting.py
// entre crochets, ex. "Return [%]")).
// ---------------------------------------------------------------------------

export const METRIC_GLOSSARY = {
  exposure_time:
    "Temps d'exposition : pourcentage du temps ou le capital etait reellement investi (position ouverte) plutot qu'en cash. Une exposition plus faible signifie moins de risque de marche pris, mais aussi moins d'opportunites saisies.",
  equity_final: "Capital final : valeur du portefeuille simule a la toute derniere date testee.",
  equity_peak: "Capital maximum atteint : la plus haute valeur que le portefeuille simule ait atteinte a un moment quelconque du test.",
  commissions: "Total des frais de courtage simules payes sur l'ensemble des transactions du test.",
  return_pct:
    "Rendement total sur toute la periode testee. A TOUJOURS comparer au rendement du simple « achat et conservation » (Buy & Hold Return) : une strategie active qui ne le bat pas nettement n'apporte probablement rien une fois la complexite et les frais comptes.",
  buy_hold_return_pct:
    "Rendement du simple « achat et conservation » sur la meme periode (achete au debut, ne revend jamais) - le point de comparaison de reference pour juger si une strategie active a reellement apporte quelque chose.",
  return_ann_pct:
    "Rendement annualise : le rendement total ramene a un taux annuel compose, pour pouvoir comparer des tests de duree differente.",
  volatility_ann_pct:
    "Volatilite annualisee : amplitude des fluctuations du portefeuille simule sur une base annuelle. Plus elle est elevee, plus la valeur du portefeuille a bougé dans tous les sens - un rendement eleve avec une volatilite forte est un resultat moins « confortable » qu'il n'y parait au premier regard.",
  cagr_pct:
    "CAGR - Compound Annual Growth Rate : taux de croissance annuel compose, tres proche du rendement annualise mais calcule selon la convention standard du secteur (utile pour comparer avec d'autres analyses financieres).",
  sharpe_ratio:
    "Ratio de Sharpe : rendement rapporte a la volatilite totale (hausses ET baisses). Repere generalement admis (pas une regle absolue) : en dessous de 1 = faible, entre 1 et 2 = correct a bon, au-dessus de 2 = tres bon. Mesure la qualite statistique du backtest, pas une prediction.",
  sortino_ratio:
    "Ratio de Sortino : comme le Sharpe, mais ne penalise que les baisses (les fortes hausses ne sont pas considerees comme un « risque ») - generalement plus eleve que le Sharpe pour une meme strategie. Un grand ecart entre les deux indique qu'une bonne part de la volatilite venait de hausses, pas de pertes.",
  calmar_ratio:
    "Ratio de Calmar : rendement annualise rapporte a la pire chute subie (Max. Drawdown). Repond a la question « le gain valait-il la douleur maximale traversee ? ».",
  max_drawdown_pct:
    "Perte maximale (Max. Drawdown) : la plus grosse chute entre un sommet et un creux pendant tout le test - la perte qu'il aurait fallu encaisser psychologiquement en investissant au pire moment possible.",
  avg_drawdown_pct:
    "Chute moyenne : moyenne de tous les episodes de recul du portefeuille - plus representative du quotidien que la pire chute (Max. Drawdown), qui ne montre qu'un seul evenement extreme.",
  max_drawdown_duration:
    "Duree de la pire chute : nombre de jours ecoules entre le sommet precedent la pire chute et le retour a un nouveau sommet.",
  avg_drawdown_duration: "Duree moyenne de recuperation : temps typique pour remonter au sommet precedent apres un recul.",
  num_trades: "Nombre total de transactions (achats/ventes) executees pendant le test.",
  win_rate_pct:
    "Taux de reussite : pourcentage des transactions cloturees avec un gain. Attention : une strategie peut etre rentable avec un taux de reussite sous 50% si les gains sont nettement plus gros que les pertes (voir Best/Worst Trade) - c'est la signature classique d'une strategie « suiveuse de tendance ».",
  best_trade_pct: "Meilleure transaction : le gain (en %) de la transaction la plus profitable du test.",
  worst_trade_pct: "Pire transaction : la perte (en %) de la transaction la plus couteuse du test.",
  avg_trade_pct: "Gain moyen par transaction, toutes transactions confondues (gagnantes et perdantes).",
  max_trade_duration: "Duree de la transaction la plus longue : le plus grand nombre de jours qu'une position soit restee ouverte.",
  avg_trade_duration: "Duree moyenne d'une transaction : temps typique de detention d'une position.",
  profit_factor:
    "Facteur de profit : total des gains divise par le total des pertes. Au-dessus de 1 la strategie est profitable sur la periode ; plus le chiffre est eleve, plus la marge de securite est grande (ex. 2 = les gains font le double des pertes).",
  expectancy_pct: "Esperance de gain : rendement moyen attendu par transaction, en tenant compte a la fois du taux de reussite et de la taille des gains/pertes.",
  sqn:
    "SQN - System Quality Number (methode Van Tharp) : mesure si l'avantage statistique d'une strategie est regulier/fiable ou s'il tient surtout au hasard sur peu de transactions. Repere indicatif : en dessous de 2 = faible a moyen, 3 a 5 = bon, au-dessus de 7 = exceptionnel - a lire avec prudence, surtout si le nombre de transactions (# Trades) est petit.",
  kelly_criterion:
    "Critere de Kelly : fraction du capital qu'il faudrait theoriquement risquer a chaque transaction pour maximiser la croissance a long terme, d'apres le taux de reussite et le ratio gain/perte observes. En pratique, les praticiens n'utilisent quasiment jamais le Kelly plein (trop agressif/instable) - plutot un quart ou une moitie de ce chiffre.",
  false_positive_rate_pct:
    "Taux de faux positifs : pourcentage des signaux (moteur interne uniquement) qui se sont trompes de direction - le complement du taux de reussite. Uniquement calcule par le moteur interne, qui juge chaque signal individuellement (contrairement a backtesting.py, qui simule un portefeuille continu).",
  avg_risk_reward:
    "Ratio gain/perte moyen (moteur interne uniquement) : gain moyen des signaux gagnants divise par la perte moyenne (en valeur absolue) des signaux perdants. Au-dessus de 1, les gains sont en moyenne plus gros que les pertes - peut compenser un taux de reussite sous 50%.",
  alpha_pct:
    "Alpha : surperformance (ou sous-performance) de la strategie par rapport a ce qu'un simple « achat et conservation » aurait produit, ajustee du risque pris (Beta).",
  beta: "Beta : sensibilite du portefeuille simule aux mouvements du marche/de l'actif sous-jacent - 1 signifie une sensibilite egale au marche, moins de 1 une sensibilite plus faible, plus de 1 une sensibilite amplifiee.",
};

// ---------------------------------------------------------------------------
// Fourchettes de lecture usuelles - UNIQUEMENT pour les ratios qui ont un
// repere reconnu dans la litterature financiere (Sharpe, SQN, Profit
// Factor). Meme convention non-directionnelle que analysisLabGlossary.js :
// "amber" = valeur peu courante/notable (dans un sens comme dans l'autre),
// "gray" = plage habituelle. Mesure la qualite statistique du BACKTEST
// PASSE, jamais un signal d'achat/vente sur le titre.
// ---------------------------------------------------------------------------

function classify(value, bands) {
  for (const band of bands) {
    if (value <= band.upTo) return band;
  }
  return bands[bands.length - 1];
}

const SHARPE_BANDS = [
  { upTo: 0, label: "Negatif (perte ajustee au risque)", tone: "amber" },
  { upTo: 1, label: "Sous 1 (generalement juge faible)", tone: "gray" },
  { upTo: 2, label: "1 a 2 (generalement juge correct a bon)", tone: "gray" },
  { upTo: Infinity, label: "Au-dessus de 2 (peu courant, tres bon)", tone: "amber" },
];

const SQN_BANDS = [
  { upTo: 1.6, label: "Sous 1.6 (faible)", tone: "amber" },
  { upTo: 3, label: "1.6 a 3 (moyen)", tone: "gray" },
  { upTo: 5, label: "3 a 5 (bon)", tone: "gray" },
  { upTo: Infinity, label: "Au-dessus de 5 (peu courant, tres bon)", tone: "amber" },
];

const PROFIT_FACTOR_BANDS = [
  { upTo: 1, label: "Sous 1 (strategie perdante sur la periode)", tone: "amber" },
  { upTo: 2, label: "1 a 2 (profitable, marge modeste)", tone: "gray" },
  { upTo: Infinity, label: "Au-dessus de 2 (marge confortable)", tone: "amber" },
];

// 01/08/2026 : extension des reperes de lecture au-dela de Sharpe/SQN/Profit
// Factor, a la demande d'un usage "debutant" (voir ParamsLabPanel.vue) -
// meme prudence que ci-dessus : direction reconnue dans la litterature pour
// Max Drawdown/Calmar/Sortino (plus bas/haut = generalement mieux), mais
// PAS pour le taux de reussite (Win Rate), qui n'a pas de "bon chiffre"
// universel (une strategie peut etre tres profitable sous 50% - voir
// METRIC_GLOSSARY.win_rate_pct) - on y applique donc la convention
// non-directionnelle (amber = valeur peu courante, gray = plage habituelle).

const MAX_DRAWDOWN_BANDS = [
  { upTo: 10, label: "Sous 10% (risque limite)", tone: "gray" },
  { upTo: 25, label: "10 a 25% (risque modere)", tone: "gray" },
  { upTo: Infinity, label: "Au-dessus de 25% (risque eleve)", tone: "amber" },
];

const CALMAR_BANDS = [
  { upTo: 0, label: "Negatif (perte non compensee par le rendement)", tone: "amber" },
  { upTo: 0.5, label: "Sous 0.5 (generalement juge faible)", tone: "gray" },
  { upTo: 1, label: "0.5 a 1 (generalement juge correct)", tone: "gray" },
  { upTo: Infinity, label: "Au-dessus de 1 (generalement juge bon a tres bon)", tone: "amber" },
];

const SORTINO_BANDS = [
  { upTo: 0, label: "Negatif (perte ajustee au risque de baisse)", tone: "amber" },
  { upTo: 1, label: "Sous 1 (generalement juge faible)", tone: "gray" },
  { upTo: 2, label: "1 a 2 (generalement juge correct a bon)", tone: "gray" },
  { upTo: Infinity, label: "Au-dessus de 2 (peu courant, tres bon)", tone: "amber" },
];

const WIN_RATE_BANDS = [
  { upTo: 30, label: "Sous 30% (notable - regarde la taille des gains/pertes avant de conclure)", tone: "amber" },
  { upTo: 70, label: "30 a 70% (plage habituelle)", tone: "gray" },
  { upTo: Infinity, label: "Au-dessus de 70% (notable, peu courant)", tone: "amber" },
];

const METRIC_BANDS = {
  sharpe_ratio: SHARPE_BANDS,
  sqn: SQN_BANDS,
  profit_factor: PROFIT_FACTOR_BANDS,
  max_drawdown_pct: MAX_DRAWDOWN_BANDS,
  calmar_ratio: CALMAR_BANDS,
  sortino_ratio: SORTINO_BANDS,
  win_rate_pct: WIN_RATE_BANDS,
};

/**
 * Classe une valeur de metrique dans sa fourchette de lecture usuelle -
 * retourne null si cette metrique n'a pas de repere etabli ou si la valeur
 * est manquante.
 */
export function interpretMetric(key, value) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const bands = METRIC_BANDS[key];
  if (!bands) return null;
  const band = classify(value, bands);
  return { label: band.label, tone: band.tone };
}

export function toneClasses(tone) {
  if (tone === "amber") return "bg-amber-50 text-amber-700 border-amber-300";
  return "bg-gray-100 text-gray-500 border-gray-300";
}

// ---------------------------------------------------------------------------
// Confiance du scorecard par strategie (13/08/2026 : "arbitrer entre
// strategies plutot que de juger sur un seul backtest" - voir
// backend/.../backtests/service.py::get_strategy_scorecard,
// jobs/evaluate_strategies_job.py). Un taux de reussite moyen calcule sur 2
// runs hebdomadaires n'a pas la meme valeur que sur 30 - ce badge le rend
// visible partout ou le scorecard est affiche (ParamsLabPanel.vue,
// SignalReliabilityView.vue), plutot que de laisser un chiffre nu suggerer
// une precision qu'il n'a pas encore.
// ---------------------------------------------------------------------------

export function classifyScorecardConfidence(count) {
  if (!count || count <= 0) return { label: "Aucun test evalue pour l'instant", tone: "amber" };
  if (count < 5) return { label: `Trop tot pour juger (${count} test${count > 1 ? "s" : ""} seulement)`, tone: "amber" };
  if (count < 20) return { label: `Echantillon encore limite (${count} tests)`, tone: "gray" };
  return { label: `Echantillon plus etoffe (${count} tests)`, tone: "gray" };
}

// ---------------------------------------------------------------------------
// Guide "comment lire ces resultats" (01/08/2026) - vue d'ensemble en 1-2
// phrases par groupe de metriques (voir ParamsLabPanel.vue::METRIC_GROUPS),
// affichee avant meme d'avoir lance un test, pour donner un repere a un
// debutant qui voit ce tableau pour la premiere fois.
// ---------------------------------------------------------------------------

export const GUIDE_SECTIONS = [
  {
    title: "Rendement",
    text: "Combien la strategie a gagne (ou perdu) sur la periode testee. A toujours comparer au rendement du simple achat-conservation (Buy & Hold) : une strategie qui ne le bat pas nettement n'a probablement pas apporte grand-chose une fois les frais comptes.",
  },
  {
    title: "Risque",
    text: "Ce qu'il aurait fallu encaisser en cours de route, pas seulement le resultat final. La perte maximale (Max. Drawdown) est le chiffre a regarder en premier : c'est la plus grosse chute traversee entre un sommet et un creux pendant le test.",
  },
  {
    title: "Ratios ajustes au risque",
    text: "Rapportent le rendement obtenu au risque pris pour l'obtenir (Sharpe, Sortino, Calmar). Deux strategies avec le meme rendement final n'ont pas forcement pris le meme risque en chemin - ces ratios permettent de les comparer sur un pied d'egalite.",
  },
  {
    title: "Transactions",
    text: "Le detail des achats/ventes simules : combien il y en a eu, quel pourcentage a gagne, les meilleures/pires operations. Un petit nombre de transactions (moins d'une dizaine) rend ces chiffres peu fiables - le resultat peut tenir surtout au hasard.",
  },
  {
    title: "Robustesse",
    text: "Mesure si l'avantage statistique observe est solide ou tient surtout a quelques coups de chance (SQN, Facteur de profit). A regarder en dernier, une fois le rendement et le risque compris - ce sont des indicateurs de fiabilite, pas de performance.",
  },
];

// ---------------------------------------------------------------------------
// Synthese automatique en langage clair (01/08/2026) - un paragraphe genere
// a partir des memes donnees que le tableau, pour un lecteur qui veut
// comprendre le resultat sans dechiffrer 24 lignes de chiffres. Complement
// du tableau detaille, ne le remplace pas (voir ParamsLabPanel.vue).
// ---------------------------------------------------------------------------

function toNumber(value) {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

/**
 * Construit un resume en langage naturel pour un resultat de backtest
 * (une ligne du tableau : une strategie x un horizon). Retourne null si les
 * donnees minimales (rendement) sont absentes.
 */
export function buildSynthesis(row) {
  const returnPct = toNumber(row.extra_metrics?.["Return [%]"]);
  const buyHoldPct = toNumber(row.extra_metrics?.["Buy & Hold Return [%]"]);
  const maxDrawdownPct = row.max_drawdown !== null && row.max_drawdown !== undefined ? Math.abs(Number(row.max_drawdown) * 100) : null;
  const winRatePct = row.win_rate !== null && row.win_rate !== undefined ? Number(row.win_rate) * 100 : null;
  const numTrades = row.signal_count ?? null;

  if (returnPct === null) return null;

  const sentences = [];

  if (buyHoldPct !== null) {
    const diff = returnPct - buyHoldPct;
    if (diff > 1) {
      sentences.push(
        `Sur cette periode, la strategie a rapporte ${returnPct.toFixed(1)}%, mieux que le simple achat-conservation (${buyHoldPct.toFixed(1)}%).`
      );
    } else if (diff < -1) {
      sentences.push(
        `Sur cette periode, la strategie a rapporte ${returnPct.toFixed(1)}%, moins bien que le simple achat-conservation (${buyHoldPct.toFixed(1)}%) - la complexite ajoutee n'a probablement pas ete utile ici.`
      );
    } else {
      sentences.push(
        `Sur cette periode, la strategie a rapporte ${returnPct.toFixed(1)}%, un resultat tres proche du simple achat-conservation (${buyHoldPct.toFixed(1)}%).`
      );
    }
    if (buyHoldPct > 15) sentences.push("Le marche etait globalement fortement haussier sur cette periode : meme ne rien faire aurait bien fonctionne.");
    else if (buyHoldPct > 5) sentences.push("Le marche etait globalement haussier sur cette periode.");
    else if (buyHoldPct < -15) sentences.push("Le marche etait globalement fortement baissier sur cette periode.");
    else if (buyHoldPct < -5) sentences.push("Le marche etait globalement baissier sur cette periode.");
    else sentences.push("Le marche etait globalement stable, sans tendance nette, sur cette periode.");
  } else {
    sentences.push(`Sur cette periode, la strategie a rapporte ${returnPct.toFixed(1)}%.`);
  }

  if (maxDrawdownPct !== null) {
    if (maxDrawdownPct > 25) {
      sentences.push(
        `Le risque a ete eleve : a un moment du test, le portefeuille simule a perdu jusqu'a ${maxDrawdownPct.toFixed(1)}% depuis son sommet - une baisse importante a encaisser psychologiquement.`
      );
    } else if (maxDrawdownPct > 10) {
      sentences.push(`Le risque a ete modere : la plus grosse chute a atteint ${maxDrawdownPct.toFixed(1)}% depuis un sommet.`);
    } else {
      sentences.push(`Le risque est reste limite : la plus grosse chute n'a ete que de ${maxDrawdownPct.toFixed(1)}%.`);
    }
  }

  if (numTrades !== null) {
    if (numTrades < 10) {
      sentences.push(
        `Attention : seulement ${numTrades} transaction${numTrades > 1 ? "s" : ""} sur ce test - trop peu pour tirer une conclusion fiable, ces chiffres peuvent tenir surtout au hasard.`
      );
    } else if (winRatePct !== null) {
      sentences.push(`${numTrades} transactions ont ete effectuees, avec ${winRatePct.toFixed(0)}% de reussite.`);
    }
  }

  return sentences.join(" ");
}
