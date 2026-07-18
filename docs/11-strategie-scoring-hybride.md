# 11. Stratégie de scoring hybride

## Structure du score : quatre composantes indépendantes

1. **Score technique** (0-100) : dérivé des indicateurs de `market_data` (doc 10), reflète la dynamique de prix/volume.
2. **Score news** (0-100) : dérivé du sentiment et des mots-clés pondérés de `news` (doc 09), reflète le contexte informationnel.
3. **Score de risque** (0-100, où 100 = risque élevé) : dérivé de la volatilité, de la présence de mots-clés à fort impact négatif (dette, dilution), et de la dispersion des composantes précédentes.
4. **Score de confiance** (0-100) : ne mesure pas la probabilité de gain, mais **la fiabilité des données disponibles** — quantité d'historique de prix, fraîcheur et nombre d'articles de news, accord/désaccord entre le score technique et le score news.

## Pourquoi ces quatre scores restent séparés (jamais fusionnés en un seul nombre opaque)
Un score unique masquerait la source du signal. Séparer permet à l'utilisateur de voir immédiatement *pourquoi* un signal est ce qu'il est ("le score technique est positif mais le score de confiance est bas car il n'y a presque pas de news récentes") — condition nécessaire de l'explicabilité exigée dès la vision produit (doc 01).

## Moteur V1 : règles pondérées explicites

```python
# Pseudo-code simplifié — voir backend/app/domains/signals/models_ml/baseline_rules.py
def compute_technical_score(features: TechnicalFeatures) -> float:
    score = 50.0  # neutre par défaut
    score += 15 if features.trend_direction == "up" else -15 if features.trend_direction == "down" else 0
    score += 10 if features.rsi_14 < 30 else -10 if features.rsi_14 > 70 else 0
    score += 10 if features.macd_cross == "bullish" else -10 if features.macd_cross == "bearish" else 0
    score -= min(15, features.volatility_20d * 100)  # forte volatilité pénalise la lisibilité du signal
    return clamp(score, 0, 100)

def compute_final_signal(technical, news, risk, confidence) -> str:
    combined = 0.5 * technical + 0.5 * news
    if confidence < 30:
        return "surveillance"          # pas assez de données fiables pour trancher
    if combined >= 70 and risk < 50:
        return "achat_speculatif"
    if combined >= 55:
        return "surveillance"
    if combined <= 30 and risk >= 60:
        return "vente_defensive"
    if combined <= 45:
        return "prudence"
    return "neutre"
```

Les poids (0.5/0.5, seuils 70/55/45/30) sont **des paramètres de configuration versionnés**, pas des constantes magiques dans le code — ils sont ajustés par la mesure du backtesting, jamais par intuition seule.

## Pourquoi les règles restent le socle même après l'introduction d'un modèle statistique (V2)
Un modèle de régression logistique ou de gradient boosting est introduit en V2 **en parallèle**, jamais en remplacement pur : les deux moteurs tournent sur les mêmes features, produisent chacun un `SignalResult` marqué par leur `engine_version`, et sont comparés en continu par backtesting. Le passage d'un modèle statistique en production ne se fait que s'il **surperforme mesurablement** la baseline de règles sur une période de validation suffisante, et son "explication" doit rester possible (feature importance globale + contribution locale type SHAP, restituée dans le même format `signal_explanations` que les règles).

## Score de confiance : formule V1

```python
def compute_confidence_score(features: SignalFeatures) -> float:
    data_completeness = features.price_history_days / 250  # sur 1 an
    news_freshness = 1.0 if features.days_since_last_news <= 3 else 0.5 if features.days_since_last_news <= 10 else 0.1
    agreement = 1.0 - abs(features.technical_score - features.news_score) / 100  # accord entre composantes
    confidence = 100 * (0.4 * min(data_completeness, 1.0) + 0.3 * news_freshness + 0.3 * agreement)
    return clamp(confidence, 0, 100)
```

Le score de confiance **n'est jamais caché** dans l'UI, et **conditionne l'affichage** : en dessous d'un seuil (30), le signal final est forcé à "surveillance" quel que soit le score combiné — l'application préfère dire "je ne sais pas assez" plutôt que d'afficher un signal tranché sur des données insuffisantes.

## Génération de l'explication textuelle

Chaque composante génère sa phrase via un **template déterministe** (pas de génération libre), rempli avec les valeurs réelles des features ayant contribué : "Le RSI (14 jours) est à {valeur}, {interprétation}." Le poids relatif (`contribution_pct`) de chaque composante dans le score final est calculé et stocké, permettant à l'UI de trier les explications par importance décroissante.

## Le signal final n'est jamais un ordre
Le vocabulaire ("achat spéculatif", "surveillance", "neutre", "prudence", "vente défensive") est choisi pour ne jamais évoquer un ordre à exécuter, conformément à la gouvernance du risque (doc 01/17). Chaque libellé est systématiquement accompagné d'un disclaimer et du score de confiance dans l'API et l'UI — contrainte vérifiée automatiquement par `compliance/guardrails.py` (doc 06).

## Mise a jour : modele statistique V2 implemente (apercu, pas remplacement)

Contrairement au squelette initial (`NotImplementedError`), la regression logistique
(`models_ml/logistic_model.py`) est desormais reellement entrainee et exposee via le
champ `ml_preview` de chaque signal - toujours en complement du signal officiel
(moteur de regles), jamais a sa place.

**Astuce de conception** : les donnees d'entrainement sont reconstruites a partir de
`signal_explanations.supporting_data` (deja stocke pour l'explicabilite), pas d'une
table dediee - aucune migration necessaire pour demarrer l'apprentissage.

**Statut de maturite explicite** (`model_status`), pense pour ne jamais laisser un
modele sous-entraine paraitre fiable :
- `en_apprentissage` : moins de `MIN_TRAINING_SAMPLES` (50, ajustable) exemples
  disponibles, tous actifs confondus. Affiche en orange cote frontend (`SignalCard.vue`).
- `fiable` : seuil atteint. Affiche en vert. Reste un second avis, jamais le signal
  affiche comme officiel - la bascule en signal principal ne se fera que si une
  comparaison par backtesting (voir doc 02, module backtests) prouve sa superiorite
  mesuree sur la duree, conformement a la regle de gouvernance du risque (doc 17).

Le module `backtests` a egalement ete branche reellement (`run_backtest_for_asset`) :
il rejoue les signaux passes contre les rendements reels constates, ce qui est le
mecanisme qui permettra a terme de comparer objectivement `rules_v1` et `logistic_v1`.
