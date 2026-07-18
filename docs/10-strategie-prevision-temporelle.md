# 10. Stratégie de prévision temporelle — comparaison réaliste

## Ce que "prévision" veut dire ici
Pas une prédiction de prix futur précis (irréaliste et dangereux à promettre), mais une **caractérisation probabiliste de la dynamique actuelle** : direction de tendance, force du momentum, niveau de volatilité, probabilité qu'un changement de régime soit en cours. C'est la différence entre "je prédis que le prix sera à 42€ vendredi" (à proscrire) et "le momentum est baissier avec une confiance modérée, la volatilité a doublé sur 10 jours" (ce que fait l'application).

## Comparaison des approches envisagées

| Approche | Description | Avantages | Limites | Décision |
|---|---|---|---|---|
| **Règles + scores pondérés** | Combinaisons explicites d'indicateurs (croisement de moyennes mobiles, RSI, ROC) avec des seuils et des poids fixés | 100% interprétable, aucun besoin d'entraînement, rapide à implémenter et à corriger | Rigide, ne s'adapte pas automatiquement, poids arbitraires au départ (à calibrer par backtesting) | **Retenue en V1**, baseline permanente |
| **Régression / régression logistique** | Prédit une probabilité de hausse/baisse à horizon N jours à partir des features techniques + news | Toujours interprétable (coefficients lisibles), entraînable avec un historique modeste, rapide | Suppose une relation linéaire entre features et cible (souvent trop simple pour les marchés) | **Retenue en V2**, comparée à la baseline sur le même jeu de backtesting |
| **Gradient boosting (LightGBM/XGBoost)** | Modèle d'ensemble d'arbres, capture des interactions non linéaires entre features | Bonne performance empirique sur données tabulaires, gère features hétérogènes (techniques + news + méta), feature importance disponible (SHAP) pour garder de l'explicabilité | Plus de risque de surapprentissage sur peu de données, demande un pipeline de validation croisée temporelle rigoureux (pas de fuite de données futures) | **Envisagée en V2**, seulement si le volume de données de backtesting est suffisant et si la régression logistique montre ses limites de façon mesurée |
| **Modèles de séries temporelles simples (ARIMA/ETS)** | Modélise la série de prix/rendements elle-même (autocorrélation, saisonnalité) | Bien établis statistiquement, bons pour caractériser la volatilité (GARCH) et détecter des ruptures | Moins adaptés pour intégrer des features exogènes (news) nativement, prévision de prix pur peu fiable à moyen/long terme | **Utilisée en V2 en complément**, notamment pour la modélisation de la volatilité (GARCH) et la détection de rupture (CUSUM), pas pour prédire un prix cible |
| **Modèle plus avancé (deep learning séquentiel, LSTM/Transformer temporel)** | Réseaux de neurones sur séquences de prix | Capacité théorique à capturer des motifs complexes | Demande un volume de données et une puissance de calcul disproportionnés pour un usage particulier, boîte noire difficile à expliquer, risque élevé de surapprentissage sur bruit de marché | **Non retenue**, sauf preuve forte que les approches plus simples plafonnent réellement (peu probable vu le rapport signal/bruit des marchés actions) |

## Détection de tendance par horizon (implémentation V1)

- **Court terme (5-20 jours)** : régression linéaire glissante sur le prix de clôture (pente normalisée) + position par rapport à la SMA20 + RSI14 (survente/surachat).
- **Moyen terme (1-3 mois)** : croisement SMA20/SMA50 (golden cross / death cross), ROC sur 60 jours.
- **Long terme (6-12 mois)** : position par rapport à la SMA200, pente de régression sur 6-12 mois, comparaison à la volatilité historique de l'actif (contexte : une tendance haussière dans un actif très volatil est moins fiable qu'une tendance haussière stable).

## Détection de rupture et de retournement

**V1** : franchissement de bande de Bollinger (signal simple de sur-extension), changement de signe du MACD (croisement de la ligne de signal), variation brutale du volume (> 2 écarts-types de la moyenne mobile du volume) comme proxy d'un possible événement significatif.

**V2** : détection de changement de régime plus robuste (CUSUM ou Bayesian online changepoint detection) sur la série des rendements, pour distinguer un bruit normal d'un vrai changement de dynamique — actuellement, les règles V1 génèrent plus de faux positifs sur les marchés volatils, mesuré via le backtesting (doc 02/06).

## Volatilité

**V1** : écart-type des rendements journaliers sur fenêtre glissante (20 jours), simple et suffisant pour classer le risque en catégories (faible/modérée/élevée).

**V2** : modèle GARCH(1,1) pour une estimation de volatilité conditionnelle (qui réagit plus vite aux chocs récents qu'un écart-type glissant simple), utile pour affiner le score de risque.

## Validation méthodologique (essentielle, pour éviter la fuite de données)
Toute comparaison entre approches (règles vs régression vs gradient boosting) est faite via **validation croisée temporelle stricte** (walk-forward) : le modèle n'est jamais évalué sur une période qui précède ses données d'entraînement. C'est la même infrastructure que le module de backtesting (doc 02) qui sert à cette comparaison — un seul mécanisme de mesure de performance pour les signaux ET pour la sélection de modèle.
