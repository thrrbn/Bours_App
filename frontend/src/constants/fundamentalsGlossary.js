/**
 * Glossaire pedagogique de la Fiche titre (fondamentaux Yahoo Finance) -
 * meme esprit que analysisLabGlossary.js : chaque terme technique doit etre
 * explicable d'un survol de souris. Voir backend/app/domains/assets/
 * fundamentals_provider.py pour la source exacte de chaque champ.
 */

export const FUNDAMENTALS_GLOSSARY = {
  market_cap:
    "Capitalisation boursiere : valeur totale de l'entreprise en bourse (nombre d'actions x cours). Sert a comparer la « taille » des entreprises entre elles (grande/moyenne/petite capitalisation).",
  trailing_pe:
    "PER (Price/Earnings) sur les 12 derniers mois : combien de fois le benefice annuel le cours de bourse represente. Un PER eleve peut signaler une entreprise chere (ou tres attendue par le marche), un PER bas une entreprise decotee (ou en difficulte) - a comparer au secteur, jamais isolement.",
  forward_pe:
    "PER previsionnel : meme calcul que le PER classique, mais base sur le benefice ATTENDU des 12 prochains mois (estimation des analystes) plutot que le benefice deja realise.",
  dividend_yield:
    "Rendement du dividende : dividende annuel verse, rapporte au cours de l'action (en %). Un rendement eleve peut signaler soit une politique genereuse, soit un cours qui a beaucoup baisse (le rendement grimpe mecaniquement) - a verifier avant de conclure.",
  week52_range:
    "Fourchette 52 semaines : plus bas et plus haut cours atteints sur les 12 derniers mois. Situe le cours actuel dans son historique recent.",
  beta: "Beta : mesure la sensibilite du titre aux mouvements du marche global. Beta = 1 -> bouge comme le marche ; > 1 -> amplifie les mouvements (plus volatil) ; < 1 -> les amortit.",
  sector:
    "Secteur d'activite (classification Yahoo Finance) - sert de base a la comparaison avec les autres actifs suivis du meme secteur.",
  industry:
    "Industrie : sous-categorie plus precise que le secteur (ex. secteur « Technologie », industrie « Semi-conducteurs »).",
  sector_comparison:
    "Comparatif secteur : moyenne calculee sur les AUTRES actifs suivis du meme secteur dont les fondamentaux ont deja ete rafraichis dans cette app - pas une moyenne de marche officielle, elle s'enrichit au fil de tes rafraichissements.",
  return_on_equity:
    "ROE (Return on Equity) : benefice net rapporte aux capitaux propres (en %). Mesure la rentabilite de l'entreprise pour ses actionnaires - combien elle degage de benefice avec l'argent qu'ils ont investi. Un ROE eleve n'est pas automatiquement bon signe : il peut aussi venir d'un fort endettement (a regarder avec la dette/capitaux propres).",
  debt_to_equity:
    "Dette / capitaux propres (Debt/Equity) : compare ce que l'entreprise doit a ce qu'elle possede en fonds propres. Plus le ratio est eleve, plus l'entreprise s'appuie sur la dette pour financer son activite - plus de risque en cas de retournement, mais parfois normal selon le secteur (ex. utilities, foncieres).",
  profit_margin:
    "Marge nette : part du chiffre d'affaires qui devient du benefice net (en %). Mesure l'efficacite globale de l'entreprise a transformer ses ventes en profit, apres toutes ses charges.",
  price_to_book:
    "P/B (Price/Book) : cours de l'action rapporte a la valeur comptable par action (actif net de l'entreprise). Un P/B bas peut signaler une decote (ou une entreprise en difficulte), un P/B eleve une prime payee par le marche (croissance attendue, actifs immateriels type marque/brevets peu visibles au bilan).",
  ev_to_ebitda:
    "VE/EBITDA (Enterprise Value/EBITDA) : valeur d'entreprise (capitalisation + dette nette) rapportee a l'EBITDA (resultat avant interets, impots, depreciation, amortissement). Souvent utilise pour comparer des entreprises entre elles independamment de leur structure de financement (dette vs capital) - plus bas peut signaler une decote relative.",
};

export function fmtMarketCap(value) {
  if (value === null || value === undefined) return "n/d";
  const abs = Math.abs(value);
  if (abs >= 1e12) return (value / 1e12).toFixed(2) + " T";
  if (abs >= 1e9) return (value / 1e9).toFixed(2) + " Md";
  if (abs >= 1e6) return (value / 1e6).toFixed(2) + " M";
  return value.toLocaleString("fr-FR");
}

// ---------------------------------------------------------------------------
// Fourchettes de lecture ("bon chiffre ou pas ?") - reperes GENERIQUES tres
// approximatifs (litterature financiere courante), a prendre avec beaucoup
// plus de prudence que les fourchettes du Labo d'analyse : contrairement a
// un RSI (formule fixe, convention universelle), "un bon PER" varie enormement
// par secteur, par cycle economique et par pays - ces bandes servent a situer
// un chiffre par rapport a des reperes generaux, jamais a juger un titre.
// Ton volontairement gris partout sauf quand la litterature signale un vrai
// point de vigilance (rendement de dividende inhabituellement eleve, beta
// nettement superieur a 1) - jamais de vert/rouge, ce n'est pas un signal.
// ---------------------------------------------------------------------------

function classify(value, bands) {
  for (const band of bands) {
    if (value <= band.upTo) return band;
  }
  return bands[bands.length - 1];
}

export function interpretPE(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const bands = [
    { upTo: 0, label: "Negatif (benefices negatifs - PER peu interpretable)", tone: "amber" },
    { upTo: 15, label: "Plutot bas par rapport aux reperes generaux (< 15)", tone: "gray" },
    { upTo: 25, label: "Dans la moyenne generale du marche (15 a 25)", tone: "gray" },
    { upTo: Infinity, label: "Plutot eleve par rapport aux reperes generaux (> 25)", tone: "gray" },
  ];
  return { ...classify(value, bands), rangeNote: "reperes generiques tres approximatifs, varie fortement par secteur" };
}

export function interpretDividendYield(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const bands = [
    { upTo: 0, label: "Pas de dividende verse actuellement", tone: "gray" },
    { upTo: 1, label: "Rendement faible (< 1%)", tone: "gray" },
    { upTo: 4, label: "Rendement courant sur le marche (1 a 4%)", tone: "gray" },
    { upTo: 8, label: "Rendement eleve (4 a 8%) - a verifier (politique genereuse ou cours en baisse ?)", tone: "amber" },
    { upTo: Infinity, label: "Rendement tres eleve (> 8%) - verifie que ce n'est pas du a une chute recente du cours", tone: "amber" },
  ];
  return { ...classify(value, bands), rangeNote: "en %, reperes generiques" };
}

export function interpretBeta(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const bands = [
    { upTo: 0.8, label: "Moins volatil que le marche (beta < 0.8)", tone: "gray" },
    { upTo: 1.2, label: "Proche du marche (beta 0.8 a 1.2)", tone: "gray" },
    { upTo: Infinity, label: "Plus volatil que le marche (beta > 1.2)", tone: "amber" },
  ];
  return { ...classify(value, bands), rangeNote: "1 = bouge comme le marche" };
}

export function interpretMarketCap(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const bands = [
    { upTo: 2e9, label: "Petite capitalisation (« small cap », < 2 Md)", tone: "gray" },
    { upTo: 10e9, label: "Moyenne capitalisation (« mid cap », 2 a 10 Md)", tone: "gray" },
    { upTo: Infinity, label: "Grande capitalisation (« large cap », > 10 Md)", tone: "gray" },
  ];
  return { ...classify(value, bands), rangeNote: "seuils generiques, en devise du titre" };
}

export function interpretReturnOnEquity(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const pct = value * 100;
  const bands = [
    { upTo: 0, label: "Negatif (l'entreprise perd de l'argent sur la periode)", tone: "amber" },
    { upTo: 10, label: "Plutot faible par rapport aux reperes generaux (< 10%)", tone: "gray" },
    { upTo: 20, label: "Dans la moyenne generale du marche (10 a 20%)", tone: "gray" },
    { upTo: Infinity, label: "Plutot eleve (> 20%) - verifie que ce n'est pas du a un fort endettement", tone: "amber" },
  ];
  return { ...classify(pct, bands), rangeNote: "en %, reperes generiques" };
}

export function interpretDebtToEquity(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const bands = [
    { upTo: 50, label: "Endettement faible par rapport aux capitaux propres (< 0.5x)", tone: "gray" },
    { upTo: 100, label: "Endettement modere (0.5x a 1x)", tone: "gray" },
    { upTo: 200, label: "Endettement eleve (1x a 2x) - a regarder selon le secteur", tone: "amber" },
    { upTo: Infinity, label: "Endettement tres eleve (> 2x) - a verifier selon le secteur (normal pour certains, ex. foncieres)", tone: "amber" },
  ];
  // yfinance renvoie debtToEquity generalement en "pourcentage" (ex. 120 = 1.2x)
  return { ...classify(value, bands), rangeNote: "reperes generiques, varie fortement par secteur" };
}

export function interpretProfitMargin(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const pct = value * 100;
  const bands = [
    { upTo: 0, label: "Negatif (l'entreprise est en perte)", tone: "amber" },
    { upTo: 5, label: "Marge faible (< 5%)", tone: "gray" },
    { upTo: 15, label: "Marge courante (5 a 15%)", tone: "gray" },
    { upTo: Infinity, label: "Marge elevee (> 15%)", tone: "gray" },
  ];
  return { ...classify(pct, bands), rangeNote: "en %, reperes generiques" };
}

export function interpretPriceToBook(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const bands = [
    { upTo: 1, label: "En dessous de la valeur comptable (< 1x) - decote ou difficultes a verifier", tone: "amber" },
    { upTo: 3, label: "Dans la moyenne generale du marche (1 a 3x)", tone: "gray" },
    { upTo: Infinity, label: "Prime elevee par rapport a la valeur comptable (> 3x)", tone: "gray" },
  ];
  return { ...classify(value, bands), rangeNote: "reperes generiques, varie fortement par secteur" };
}

export function interpretEvToEbitda(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const bands = [
    { upTo: 0, label: "Negatif ou EBITDA negatif (peu interpretable)", tone: "amber" },
    { upTo: 8, label: "Plutot bas par rapport aux reperes generaux (< 8x)", tone: "gray" },
    { upTo: 15, label: "Dans la moyenne generale du marche (8 a 15x)", tone: "gray" },
    { upTo: Infinity, label: "Plutot eleve (> 15x)", tone: "gray" },
  ];
  return { ...classify(value, bands), rangeNote: "reperes generiques, varie fortement par secteur" };
}

export function toneClasses(tone) {
  if (tone === "amber") return "bg-amber-50 text-amber-700 border-amber-300";
  return "bg-gray-100 text-gray-500 border-gray-300";
}
