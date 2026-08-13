/**
 * Glossaire pedagogique du Laboratoire d'analyse (bac a sable, voir
 * backend/app/domains/analysis_lab/). Objectif : que chaque terme technique
 * affiche a l'ecran (modele, statut, metrique, indicateur) soit explicable
 * d'un survol de souris, sans avoir a sortir de l'app - public vise : eleves
 * en formation, pas des traders confirmes.
 *
 * Les explications des indicateurs (FEATURE_*) reprennent exactement les
 * formules/periodes de backend/app/domains/analysis_lab/feature_engineering.py
 * (source de verite) - a maintenir en phase si ce fichier evolue.
 */

// ---------------------------------------------------------------------------
// Modeles
// ---------------------------------------------------------------------------

export const MODEL_GLOSSARY = {
  random_forest:
    "Random Forest : combine des centaines d'arbres de decision entraines sur des sous-echantillons differents et fait voter leurs predictions. Robuste au surapprentissage, facile a interpreter via l'importance des variables.",
  xgboost:
    "XGBoost (gradient boosting) : construit les arbres de decision un par un, chacun corrigeant les erreurs du precedent. Souvent tres performant sur donnees tabulaires, mais plus sensible au surapprentissage que Random Forest.",
  arima:
    "ARIMA (AutoRegressive Integrated Moving Average) : modele statistique classique qui predit une serie temporelle a partir de ses propres valeurs passees et de ses erreurs passees, sans utiliser les indicateurs techniques.",
  prophet:
    "Prophet (Meta/Facebook) : modele de serie temporelle concu pour detecter automatiquement tendance et saisonnalite, robuste aux donnees manquantes et aux changements de tendance.",
  ensemble:
    "Ensemble (vote) : combine les predictions des autres modeles (ponderees selon leur fiabilite) pour reduire le risque de suivre l'erreur d'un seul modele.",
  lstm:
    "LSTM (Long Short-Term Memory) : reseau de neurones recurrent concu pour apprendre des dependances dans une sequence (ici, l'historique de prix). Plus lent a entrainer qu'un Random Forest/XGBoost - c'est pourquoi il tourne en tache de fond.",
};

// ---------------------------------------------------------------------------
// Statuts de fiabilite d'un modele
// ---------------------------------------------------------------------------

export const STATUS_GLOSSARY = {
  fiable:
    "Fiable : le modele a assez d'exemples recents pour etre valide, et sa precision de validation depasse un seuil minimal.",
  en_apprentissage:
    "En apprentissage : le modele produit deja une prediction, mais n'a pas encore assez d'exemples recents pour valider sa fiabilite - a prendre avec prudence.",
  indisponible:
    "Indisponible : pas assez d'historique de prix pour entrainer ce modele sur cet actif/horizon.",
};

// ---------------------------------------------------------------------------
// Direction predite
// ---------------------------------------------------------------------------

export const DIRECTION_GLOSSARY = {
  hausse: "Le modele anticipe une hausse du prix sur l'horizon choisi.",
  baisse: "Le modele anticipe une baisse du prix sur l'horizon choisi.",
};

// ---------------------------------------------------------------------------
// Accord avec le signal reel
// ---------------------------------------------------------------------------

export const AGREEMENT_GLOSSARY = {
  true: "Ce modele va dans le meme sens que le signal reel du moteur de regles - un accord ne veut pas dire que l'un des deux a forcement raison.",
  false:
    "Ce modele va dans un sens different du signal reel du moteur de regles - un desaccord invite a la prudence, pas a trancher automatiquement en faveur de l'un ou l'autre.",
};

// ---------------------------------------------------------------------------
// Metriques de modele
// ---------------------------------------------------------------------------

export const METRIC_GLOSSARY = {
  probability_up:
    "Probabilite estimee par le modele que le prix soit plus haut a l'horizon choisi qu'aujourd'hui.",
  train_accuracy:
    "Precision (accuracy) sur les donnees qui ont servi a entrainer le modele - a interpreter avec prudence, un modele peut « apprendre par cœur » ces exemples.",
  validation_accuracy:
    "Precision sur des exemples recents JAMAIS vus pendant l'entrainement - indicateur plus fiable de la vraie capacite predictive du modele.",
  feature_importance:
    "Importance des variables : pour chaque indicateur technique, a quel point il pese dans les predictions de ce modele. Ne dit pas s'il pousse vers la hausse ou la baisse, seulement a quel point il compte.",
};

// ---------------------------------------------------------------------------
// Statut du job LSTM asynchrone
// ---------------------------------------------------------------------------

export const JOB_STATUS_GLOSSARY = {
  pending: "En attente : la demande d'entrainement a ete acceptee, le job va demarrer sous peu.",
  running: "En cours : le modele LSTM s'entraine actuellement en tache de fond (peut prendre plusieurs secondes).",
  completed: "Termine : l'entrainement est fini, le resultat est affiche ci-dessous.",
  failed: "Echec : l'entrainement a rencontre une erreur (voir le message ci-dessous).",
};

// ---------------------------------------------------------------------------
// Signal reel (moteur de regles, voir backend/.../signals/models_ml/baseline_rules.py)
// ---------------------------------------------------------------------------

export const REAL_SIGNAL_GLOSSARY = {
  achat_speculatif:
    "Achat speculatif : score combine juge suffisamment positif et risque suffisamment maitrise pour envisager un achat - reste speculatif, pas une garantie.",
  surveillance:
    "Surveillance : signal pas assez tranche (ou confiance insuffisante dans les donnees) pour agir - a suivre dans le temps.",
  vente_defensive:
    "Vente defensive : signal negatif combine a un risque eleve - une posture prudente, pas un ordre de vente automatique.",
  prudence: "Prudence : signal legerement negatif, sans declencher une posture defensive complete.",
  neutre: "Neutre : aucun biais haussier ou baissier suffisamment marque ne se degage.",
  technical_score:
    "Score technique (0-100) : combine tendance (SMA 20j vs SMA 50j), RSI 14 jours, croisement MACD et volatilite recente.",
  news_score: "Score d'actualite (0-100) : reflete le ton et le volume des actualites recentes sur cet actif.",
  risk_score:
    "Score de risque (0-100) : plus il est eleve, plus la situation est jugee risquee (volatilite, incertitude) - peut bloquer un signal d'achat meme si le score technique est bon.",
  confidence_score:
    "Score de confiance (0-100) : mesure la fiabilite des donnees utilisees pour calculer les autres scores - si trop bas, le signal bascule automatiquement en « surveillance ».",
};

// ---------------------------------------------------------------------------
// Indicateurs techniques (72 features, voir feature_engineering.py)
// ---------------------------------------------------------------------------

const FEATURE_EXACT = {
  macd: "MACD (Moving Average Convergence Divergence) : difference entre l'EMA 12 jours et l'EMA 26 jours du cours de cloture. Un MACD positif suggere un momentum haussier.",
  macd_signal:
    "Ligne de signal du MACD : EMA 9 jours du MACD lui-meme. Un croisement MACD/signal est souvent lu comme un signal d'achat ou de vente.",
  macd_histogram:
    "Histogramme MACD : ecart entre le MACD et sa ligne de signal. Son changement de signe precede souvent un croisement.",
  plus_di_14:
    "+DI (14 jours) : mesure la force du mouvement haussier recent. Compare a -DI, sert a determiner la direction de la tendance (voir ADX pour sa force).",
  minus_di_14:
    "-DI (14 jours) : mesure la force du mouvement baissier recent. Compare a +DI, sert a determiner la direction de la tendance (voir ADX pour sa force).",
  adx_14:
    "ADX (Average Directional Index, 14 jours) : mesure la FORCE d'une tendance, sans indiquer sa direction (voir +DI/-DI). Au-dessus de 25, la tendance est generalement consideree comme marquee.",
  aroon_oscillator:
    "Oscillateur Aroon : mesure depuis combien de temps le prix a touche un plus haut ou un plus bas recent (entre -100 et +100). Indique la RECENCE d'une tendance plutot que son ampleur.",
  parabolic_sar:
    "Parabolic SAR : points d'inversion de tendance suggeres, qui se rapprochent du prix a mesure que la tendance se confirme. Souvent utilise pour placer un stop suiveur.",
  stochastic_k:
    "Stochastique %K : position du dernier cours de cloture dans la fourchette haut/bas des 14 derniers jours (0-100).",
  stochastic_d: "Stochastique %D : moyenne mobile sur 3 jours du %K, utilisee comme ligne de signal.",
  cci_20:
    "CCI (Commodity Channel Index, 20 jours) : ecart du prix typique a sa moyenne mobile, normalise. Au-dela de +/-100, le prix est juge loin de sa moyenne recente.",
  williams_r_14:
    "Williams %R (14 jours) : similaire au stochastique mais inverse, entre 0 et -100. En dessous de -80 = survente, au-dessus de -20 = surachat.",
  roc_20:
    "ROC - Rate of Change (20 jours) : variation en % du cours de cloture par rapport a il y a 20 jours. Mesure directe du momentum.",
  mfi_14:
    "MFI - Money Flow Index (14 jours) : un RSI pondere par le volume. Combine prix et volume pour evaluer la pression acheteuse/vendeuse.",
  bollinger_upper:
    "Bande de Bollinger haute : moyenne mobile 20 jours + 2 ecarts-types. Le prix sort rarement au-dessus ; le franchir signale une forte poussee haussiere.",
  bollinger_lower:
    "Bande de Bollinger basse : moyenne mobile 20 jours - 2 ecarts-types. Le prix sort rarement en dessous ; le franchir signale une forte poussee baissiere.",
  bollinger_width:
    "Largeur des bandes de Bollinger : ecart entre bande haute et basse, normalise par la moyenne. Se resserre avant une phase de forte volatilite (breakout).",
  bollinger_position:
    "Position dans les bandes de Bollinger : 0 = colle a la bande basse, 1 = colle a la bande haute, 0.5 = au centre (moyenne mobile).",
  atr_14:
    "ATR - Average True Range (14 jours) : amplitude moyenne des mouvements de prix. Mesure la volatilite en valeur absolue, independamment de la direction.",
  keltner_middle:
    "Canal de Keltner - ligne mediane : EMA du cours de cloture, centre du canal (bandes haute/basse basees sur l'ATR).",
  keltner_upper: "Canal de Keltner - bande haute : ligne mediane + un multiple de l'ATR.",
  keltner_lower: "Canal de Keltner - bande basse : ligne mediane - un multiple de l'ATR.",
  historical_volatility_20:
    "Volatilite historique annualisee (20 jours) : ecart-type des rendements logarithmiques, ramene a une base annuelle - convention standard pour comparer le risque entre actifs.",
  obv: "OBV - On-Balance Volume : cumul du volume, ajoute les jours de hausse et retranche les jours de baisse. Une divergence entre le prix et l'OBV peut annoncer un retournement.",
  cmf_20:
    "CMF - Chaikin Money Flow (20 jours) : pression acheteuse ou vendeuse ponderee par le volume, entre -1 et +1.",
  vwap_20:
    "VWAP glissant (20 jours) : prix moyen pondere par le volume sur les 20 derniers jours - approximation glissante, differente du VWAP intrajournalier classique.",
  force_index_13:
    "Force Index (lisse sur 13 jours) : combine variation de prix et volume pour mesurer la force d'un mouvement.",
  day_of_week: "Jour de la semaine du cours (0 = lundi ... 4 = vendredi) - permet au modele d'apprendre d'eventuels effets calendaires.",
  month: "Mois du cours (1 a 12) - permet au modele d'apprendre d'eventuels effets saisonniers.",
  quarter: "Trimestre du cours (1 a 4) - permet au modele d'apprendre d'eventuels effets de fin de trimestre.",
  is_month_start: "Indicateur binaire (0/1) : ce jour est-il le premier jour de bourse du mois ?",
  is_month_end: "Indicateur binaire (0/1) : ce jour est-il le dernier jour de bourse du mois ? Periode parfois marquee par des rééquilibrages de portefeuille institutionnels.",
  is_quarter_start: "Indicateur binaire (0/1) : ce jour est-il le premier jour de bourse du trimestre ?",
  is_quarter_end: "Indicateur binaire (0/1) : ce jour est-il le dernier jour de bourse du trimestre ? Periode parfois marquee par des rééquilibrages de portefeuille institutionnels.",
  day_of_week_sin: "Encodage cyclique (sinus) du jour de la semaine : evite qu'un modele croie que « vendredi » et « lundi » sont loin l'un de l'autre alors qu'ils sont adjacents dans le cycle.",
  day_of_week_cos: "Encodage cyclique (cosinus) du jour de la semaine : complement du sinus, meme objectif (representer un cycle sans rupture artificielle).",
  month_sin: "Encodage cyclique (sinus) du mois : evite qu'un modele croie que « decembre » et « janvier » sont loin l'un de l'autre alors qu'ils sont adjacents dans le cycle.",
  month_cos: "Encodage cyclique (cosinus) du mois : complement du sinus, meme objectif (representer un cycle sans rupture artificielle).",
  returns_mean_20: "Rendement moyen des 20 derniers jours.",
  returns_std_20: "Ecart-type des rendements sur 20 jours - mesure de volatilite a court terme.",
  returns_min_20: "Rendement journalier minimum observe sur les 20 derniers jours.",
  returns_max_20: "Rendement journalier maximum observe sur les 20 derniers jours.",
  returns_skew_20:
    "Asymetrie (skewness) des rendements sur 20 jours - une skew negative signale des baisses plus extremes que les hausses.",
  returns_kurt_20:
    "Aplatissement (kurtosis) des rendements sur 20 jours - une kurtosis elevee signale des mouvements extremes plus frequents que sous une distribution normale.",
  price_range: "Amplitude du jour : ecart entre le plus haut et le plus bas.",
  price_position: "Position de la cloture dans l'amplitude du jour (0 = cloture au plus bas, 1 = cloture au plus haut).",
  price_gap: "Ecart d'ouverture (gap) : difference entre le cours d'ouverture du jour et la cloture de la veille.",
  is_doji: "Doji (0/1) : chandelier ou ouverture et cloture sont quasi identiques - signale une indecision du marche.",
  is_bullish_engulfing:
    "Avalement haussier (0/1) : bougie haussiere qui « avale » entierement le corps de la bougie baissiere precedente - pattern de retournement haussier.",
  is_bearish_engulfing:
    "Avalement baissier (0/1) : bougie baissiere qui « avale » entierement le corps de la bougie haussiere precedente - pattern de retournement baissier.",
  is_hammer:
    "Marteau (0/1) : petite bougie avec une longue meche basse - pattern souvent lu comme un signal de retournement haussier apres une baisse.",
};

const FEATURE_PATTERNS = [
  {
    re: /^sma_(\d+)$/,
    fn: (n) =>
      `Moyenne mobile simple (SMA) sur ${n} jours : moyenne arithmetique des ${n} derniers cours de cloture. Lisse les variations de prix pour degager la tendance de fond.`,
  },
  {
    re: /^ema_(\d+)$/,
    fn: (n) =>
      `Moyenne mobile exponentielle (EMA) sur ${n} jours : comme la SMA, mais donne plus de poids aux cours recents - reagit plus vite aux changements de tendance.`,
  },
  {
    re: /^rsi_(\d+)$/,
    fn: (n) =>
      `RSI - Relative Strength Index (${n} jours) : oscillateur entre 0 et 100 qui compare l'ampleur des hausses et des baisses recentes. Au-dessus de 70 = zone de surachat, en dessous de 30 = zone de survente.`,
  },
  {
    re: /^close_lag_(\d+)$/,
    fn: (n) => `Cours de cloture il y a ${n} jour${n > 1 ? "s" : ""} - donne au modele un acces explicite a l'historique recent des prix.`,
  },
];

/**
 * Retourne l'explication pedagogique d'un indicateur technique par son nom
 * de colonne exact (ex: "rsi_14", "bollinger_position"), ou null si inconnu.
 */
export function explainFeature(name) {
  if (Object.prototype.hasOwnProperty.call(FEATURE_EXACT, name)) return FEATURE_EXACT[name];
  for (const { re, fn } of FEATURE_PATTERNS) {
    const match = name.match(re);
    if (match) return fn(...match.slice(1));
  }
  return null;
}

// ---------------------------------------------------------------------------
// Fourchettes de lecture ("bon chiffre ou pas ?") - UNIQUEMENT pour les
// indicateurs bornes avec une convention de lecture etablie (oscillateurs
// 0-100, -100/+100, etc.). Volontairement absent pour SMA/EMA/lags/features
// temporelles/statistiques de rendement : leur echelle depend du prix de
// l'actif ou n'a pas de "bonne valeur" universelle - un badge y serait
// trompeur. Le ton ("amber" = zone extreme/inhabituelle, "gray" = zone
// centrale/neutre) est volontairement NON directionnel : une zone de
// survente/surachat decrit un ETAT, ce n'est jamais un signal d'achat/vente
// (voir disclaimer du domaine analysis_lab).
// ---------------------------------------------------------------------------

function classify(value, bands) {
  for (const band of bands) {
    if (value <= band.upTo) return band;
  }
  return bands[bands.length - 1];
}

const RSI_BANDS = [
  { upTo: 30, label: "Zone basse (survente, < 30)", tone: "amber" },
  { upTo: 70, label: "Zone neutre (30 a 70)", tone: "gray" },
  { upTo: Infinity, label: "Zone haute (surachat, > 70)", tone: "amber" },
];

const STOCHASTIC_MFI_BANDS = [
  { upTo: 20, label: "Zone basse (survente, < 20)", tone: "amber" },
  { upTo: 80, label: "Zone neutre (20 a 80)", tone: "gray" },
  { upTo: Infinity, label: "Zone haute (surachat, > 80)", tone: "amber" },
];

const WILLIAMS_R_BANDS = [
  { upTo: -80, label: "Zone basse (survente, < -80)", tone: "amber" },
  { upTo: -20, label: "Zone neutre (-80 a -20)", tone: "gray" },
  { upTo: Infinity, label: "Zone haute (surachat, > -20)", tone: "amber" },
];

const CCI_BANDS = [
  { upTo: -100, label: "En dessous de -100 (ecart marque sous la moyenne)", tone: "amber" },
  { upTo: 100, label: "Zone neutre (-100 a 100)", tone: "gray" },
  { upTo: Infinity, label: "Au dessus de +100 (ecart marque au dessus de la moyenne)", tone: "amber" },
];

const AROON_BANDS = [
  { upTo: -50, label: "Proche de -100 (le plus bas recent domine)", tone: "amber" },
  { upTo: 50, label: "Zone neutre (-50 a 50)", tone: "gray" },
  { upTo: Infinity, label: "Proche de +100 (le plus haut recent domine)", tone: "amber" },
];

const BOLLINGER_POSITION_BANDS = [
  { upTo: 0.1, label: "Proche de la bande basse (< 0.1)", tone: "amber" },
  { upTo: 0.9, label: "Dans le canal (0.1 a 0.9)", tone: "gray" },
  { upTo: Infinity, label: "Proche de la bande haute (> 0.9)", tone: "amber" },
];

const ADX_BANDS = [
  { upTo: 20, label: "Tendance faible ou absente (< 20)", tone: "gray" },
  { upTo: 25, label: "Tendance naissante (20 a 25)", tone: "gray" },
  { upTo: 50, label: "Tendance marquee (25 a 50)", tone: "amber" },
  { upTo: Infinity, label: "Tendance tres forte (> 50)", tone: "amber" },
];

const FEATURE_RANGE_EXACT = {
  stochastic_k: { bands: STOCHASTIC_MFI_BANDS, rangeNote: "0 a 100" },
  stochastic_d: { bands: STOCHASTIC_MFI_BANDS, rangeNote: "0 a 100" },
  mfi_14: { bands: STOCHASTIC_MFI_BANDS, rangeNote: "0 a 100" },
  williams_r_14: { bands: WILLIAMS_R_BANDS, rangeNote: "-100 a 0" },
  cci_20: { bands: CCI_BANDS, rangeNote: "generalement -100 a 100, peut deborder" },
  aroon_oscillator: { bands: AROON_BANDS, rangeNote: "-100 a 100" },
  bollinger_position: { bands: BOLLINGER_POSITION_BANDS, rangeNote: "0 a 1 (peut deborder legerement)" },
  adx_14: { bands: ADX_BANDS, rangeNote: "0 a 100" },
};

const RANGE_PATTERNS = [{ re: /^rsi_\d+$/, spec: { bands: RSI_BANDS, rangeNote: "0 a 100" } }];

/**
 * Classe une valeur d'indicateur dans sa fourchette de lecture usuelle -
 * retourne null si cet indicateur n'a pas de convention etablie (ex. SMA,
 * lags, features temporelles) ou si la valeur est manquante. `tone` vaut
 * "amber" (zone extreme/inhabituelle) ou "gray" (zone centrale/neutre) -
 * jamais un jugement "bon/mauvais", encore moins un signal d'achat/vente.
 */
export function interpretFeature(name, value) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  let spec = FEATURE_RANGE_EXACT[name];
  if (!spec) {
    const match = RANGE_PATTERNS.find(({ re }) => re.test(name));
    if (match) spec = match.spec;
  }
  if (!spec) return null;
  const band = classify(value, spec.bands);
  return { label: band.label, tone: band.tone, rangeNote: spec.rangeNote };
}

// ---------------------------------------------------------------------------
// Laboratoire d'indicateurs (13/08/2026, voir backend/.../feature_engineering.py::
// ADJUSTABLE_INDICATORS) : explication du CALCUL (formule/methode, pas
// seulement la definition deja donnee par FEATURE_EXACT/explainFeature ci-
// dessus) - reponse a "comment est-ce que ce chiffre a ete obtenu ?", pour
// chaque indicateur recalculable avec des parametres personnalises. Cle =
// indicator_key du registre backend (ex. "rsi"), pas le nom de colonne
// (qui peut varier avec la periode choisie, ex. rsi_7 vs rsi_21).
// ---------------------------------------------------------------------------

export const INDICATOR_HOW_CALCULATED = {
  adx: "1) Calcule le mouvement directionnel positif/negatif (+DM/-DM) jour par jour a partir des plus hauts/plus bas. 2) Lisse +DM/-DM et l'amplitude (True Range) sur la periode choisie pour obtenir +DI/-DI. 3) DX = 100 x |+DI - -DI| / (+DI + -DI). 4) ADX = moyenne lissee de DX sur la meme periode.",
  aroon: "Pour chaque jour : Aroon Up = 100 x (periode - jours depuis le plus haut de la periode) / periode, Aroon Down = meme calcul avec le plus bas. L'oscillateur affiche = Aroon Up - Aroon Down.",
  rsi: "1) Calcule les variations de cloture jour par jour, separees en hausses et baisses. 2) Lisse (moyenne mobile exponentielle) les hausses moyennes et les baisses moyennes sur la periode choisie. 3) RSI = 100 - [100 / (1 + hausses moyennes / baisses moyennes)].",
  stochastic: "%K = 100 x (cloture - plus bas de la periode) / (plus haut de la periode - plus bas de la periode). %D = moyenne mobile de %K sur la fenetre de lissage choisie.",
  cci: "1) Prix typique = (plus haut + plus bas + cloture) / 3. 2) Ecart du prix typique a sa moyenne mobile sur la periode. 3) CCI = ecart / (0.015 x ecart absolu moyen) - la constante 0.015 est une convention d'origine (Lambert) calibree pour que la plupart des valeurs restent entre -100 et 100.",
  williams_r: "%R = -100 x (plus haut de la periode - cloture) / (plus haut de la periode - plus bas de la periode) - tres proche du stochastique %K, mais sur une echelle -100 a 0.",
  roc: "Taux de variation = (cloture aujourd'hui - cloture il y a N jours) / cloture il y a N jours x 100, N = periode choisie.",
  mfi: "Comme le RSI, mais pondere par le volume : 1) Prix typique x volume = flux monetaire brut. 2) Separe en flux positif/negatif selon que le prix typique monte ou baisse. 3) Meme formule que le RSI, appliquee au ratio flux positif / flux negatif sur la periode.",
  bollinger: "1) Bande du milieu = moyenne mobile simple sur la periode. 2) Ecart-type des cours sur la meme periode. 3) Bande haute = milieu + (ecarts-types x ecart-type), bande basse = milieu - (ecarts-types x ecart-type).",
  atr: "1) True Range de chaque jour = le plus grand des trois ecarts (haut-bas du jour, haut du jour-cloture veille, bas du jour-cloture veille). 2) ATR = moyenne lissee du True Range sur la periode choisie.",
  keltner: "1) Ligne du milieu = moyenne mobile exponentielle des clotures sur la periode. 2) ATR calcule sur sa propre periode (independante de celle du milieu). 3) Bande haute = milieu + (multiplicateur x ATR), bande basse = milieu - (multiplicateur x ATR).",
  historical_volatility: "1) Calcule les rendements logarithmiques jour par jour (ln(cloture / cloture veille)). 2) Ecart-type de ces rendements sur la periode choisie. 3) Annualise en multipliant par la racine carree du nombre de jours de bourse par an (252 par convention).",
  cmf: "1) Multiplicateur de flux monetaire = [(cloture - plus bas) - (plus haut - cloture)] / (plus haut - plus bas), par jour. 2) Flux monetaire = multiplicateur x volume. 3) CMF = somme des flux monetaires sur la periode / somme des volumes sur la meme periode.",
  vwap: "Somme, sur la periode choisie, du prix typique de chaque jour multiplie par son volume, divisee par la somme des volumes sur la meme periode - une moyenne ponderee par le volume plutot qu'une simple moyenne des prix.",
};

export function toneClasses(tone) {
  if (tone === "amber") return "bg-amber-50 text-amber-700 border-amber-300";
  return "bg-gray-100 text-gray-500 border-gray-300";
}
