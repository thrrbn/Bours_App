# Guide pour élèves — comprendre et utiliser Bourse Assistant

## Avant de commencer : ce que cette application est, et n'est pas

Bourse Assistant est un **outil pédagogique de simulation boursière**. Tout ce qu'il affiche — signaux, scores, backtests, ratios financiers — est calculé à partir de données réelles (Yahoo Finance, Binance), mais **rien de ce qui s'affiche ici n'est un conseil en investissement**. Aucun argent réel n'est jamais engagé : le "portefeuille virtuel" est une simulation avec du cash fictif.

Trois règles à garder en tête tout au long de ce guide :

1. **Un signal "achat" n'est pas un ordre d'achat.** C'est le résultat d'un calcul statistique sur des données passées, pas une prédiction garantie.
2. **Un bon résultat de backtest ne garantit rien sur l'avenir.** Une stratégie qui a bien marché sur les 12 derniers mois peut très bien ne pas fonctionner sur les 12 prochains.
3. **Les données viennent de sources externes non contractuelles** (essentiellement Yahoo Finance) : elles peuvent être incomplètes, en retard, ou changer de format sans préavis. Toujours croiser avec une source de référence avant de tirer une conclusion.

Ce guide parcourt chaque page de l'application dans l'ordre où un élève les rencontrerait probablement, explique ce qu'elle montre, comment la lire, et où sont ses limites.

---

## 1. Page Marché — la photo du jour

C'est la page d'accueil. Elle affiche, **en direct** depuis Yahoo Finance et Binance (pas les titres personnellement suivis dans l'app) :

- les grands indices (CAC 40, indices américains, etc.) ;
- les plus fortes hausses et baisses du jour, par zone (France, États-Unis, Crypto) ;
- une liste de liens utiles vers des sources de référence gratuites (Yahoo Finance, Boursorama, ZoneBourse, Euronext Live, Binance) pour aller vérifier une information par soi-même.

Cette page se met à jour automatiquement trois fois par jour (7h, 12h, 17h) ; un bouton "Actualiser" permet de forcer un nouveau calcul entre deux horaires fixes.

**À retenir pour l'apprentissage** : c'est un bon point de départ pour prendre le pouls du marché avant de regarder un titre en particulier — est-ce que le marché est globalement haussier ou baissier aujourd'hui ?

---

## 2. Rechercher et suivre un actif

La page "Recherche" permet de retrouver un titre déjà suivi dans l'application (par ticker ou par nom), ou d'en ajouter un nouveau en cherchant directement son ticker exact sur Yahoo Finance (par exemple `AAPL`, `MC.PA`, `SOLB.BR`). Ajouter un titre ne coûte rien et ne déclenche aucun ordre : cela signifie juste que l'application va désormais suivre son prix, calculer ses signaux et récupérer ses actualités.

Retirer un titre ne supprime pas son historique — on peut toujours le rajouter plus tard.

---

## 3. La fiche d'un actif

Cliquer sur un titre ouvre sa fiche, organisée en deux onglets.

### Onglet "Vue d'ensemble"

On y trouve :

- **le signal du moment**, pour l'horizon choisi (voir section 4) ;
- **la tendance réelle passée** (rendement constaté sur 1, 3, 6 et 12 mois) — un point de comparaison factuel, pas une prédiction ;
- **la comparaison avec les avis externes** : le signal du moteur de règles interne, celui du modèle statistique léger, et le consensus des analystes externes (Yahoo Finance), affichés côte à côte pour voir s'ils sont d'accord ou non, avec les articles récents qui peuvent expliquer un éventuel désaccord.

### Onglet "Fiche titre"

C'est la fiche fondamentale du titre (secteur, industrie, capitalisation, PER courant et prévisionnel, rendement du dividende, fourchette de cours sur 52 semaines, beta, et cinq ratios plus avancés : **ROE** (rentabilité pour les actionnaires), **dette/capitaux propres**, **marge nette**, **P/B** (cours rapporté à la valeur comptable) et **VE/EBITDA**). Chaque chiffre est accompagné d'une étiquette qui le situe par rapport à des repères génériques (jamais un signal d'achat/vente — juste "c'est plutôt haut" ou "plutôt bas par rapport à l'usage courant").

Plus bas, un **comparatif sectoriel** : la moyenne de ces mêmes ratios chez les autres titres suivis du même secteur (calculée uniquement à partir de fiches déjà rafraîchies dans l'application, jamais un appel supplémentaire à Yahoo Finance), ainsi que la **liste des pairs individuels** utilisés pour ce calcul — utile pour comprendre d'où vient une moyenne plutôt que de la prendre pour argent comptant.

**Limite à connaître** : ces données Yahoo Finance sont fréquemment absentes pour les petites valeurs européennes, et certains champs (comme le rendement du dividende) ont déjà changé de convention par le passé sans préavis de Yahoo — un chiffre manquant ("n/d") est normal, pas un bug.

---

## 4. Comprendre un signal

Un signal est calculé pour trois horizons distincts : **court terme** (quelques jours), **moyen terme** (quelques semaines) et **long terme** (plusieurs mois) — un même titre peut très bien avoir un signal différent selon l'horizon regardé.

Il est composé de :

- un **score technique** (0 à 100), basé sur les indicateurs de prix (moyennes mobiles, RSI, MACD, etc.) ;
- un **score news** (0 à 100), basé sur le ton des articles récents ;
- un **score de risque** (0 à 100) ;
- un **score de confiance** (0 à 100), qui reflète à quel point le moteur "est sûr" de son calcul (peu de données disponibles = confiance plus basse) ;
- un **signal final** (achat / surveillance / prudence / vente, ou équivalent), qui combine tout cela ;
- des **explications textuelles**, une par composante, qui détaillent en français pourquoi le score est ce qu'il est.

Un aperçu du **modèle statistique** (une approche complémentaire, toujours secondaire) peut aussi apparaître, avec une vérification anti-surapprentissage (précision sur les données d'entraînement comparée à la précision sur des données jamais vues) — un grand écart entre les deux est un signe de méfiance.

**À retenir** : le signal officiel de l'application est toujours celui du "moteur de règles" — tout le reste (modèle statistique, modèles du Labo d'analyse) n'est affiché qu'à titre de comparaison pédagogique.

---

## 5. Le portefeuille virtuel

C'est l'endroit où l'on "achète" et "vend" des titres avec du cash simulé, au dernier cours connu (frais et taxe sur les opérations boursières inclus dans le calcul, comme pour un vrai ordre). On y trouve :

- le cash disponible, la valeur totale, le gain/perte cumulé et les frais payés ;
- la liste des positions, avec pour chacune la possibilité d'ouvrir "pourquoi ce signal ?" (le détail du signal courant sur cette position, par horizon) ;
- l'historique des transactions (achats, ventes, et dividendes crédités automatiquement) ;
- une alerte si un titre détenu a un consensus d'analystes externes penchant vers la vente (une information, jamais un ordre automatique) ;
- un bouton "Réinitialiser" pour repartir de zéro.

C'est aussi depuis une position de ce portefeuille que s'ouvre le **Labo de paramètres** (section 7).

---

## 6. Ma watchlist

Une liste de titres suivis sans forcément les détenir en portefeuille — pratique pour observer un titre avant de décider quoi que ce soit. Chaque ligne affiche le signal moyen terme courant, et mène directement à la fiche complète du titre.

---

## 7. Le Labo de paramètres — tester une stratégie sur un titre

Ouvert depuis une position du portefeuille virtuel ("tester les paramètres"), ce labo permet de rejouer un backtest (une simulation sur des données passées) en modifiant soi-même les réglages, **sans jamais toucher au vrai signal ni au portefeuille réel**. Chaque clic sur "Lancer le test" crée un test indépendant, qui n'est jamais sauvegardé comme référence.

Deux moteurs tournent en parallèle sur les mêmes paramètres, pour se recouper l'un l'autre :

- le **moteur interne** de l'application (celui qui produit les vrais signaux), rejoué avec les seuils de décision que l'on choisit ;
- **backtesting.py**, une bibliothèque tierce reconnue, qui simule un vrai portefeuille (cash, ordres, courbe de valeur) avec plusieurs stratégies au choix : croisement de moyennes mobiles (SMA), RSI, MACD, bandes de Bollinger, rejeu des signaux de l'application ("nos signaux"), et le simple "achat et conservation" (buy & hold) comme référence incontournable.

Pour chaque stratégie testée, un tableau détaillé affiche des dizaines de statistiques regroupées par thème (rendement, risque, ratios ajustés au risque, transactions, robustesse), chacune expliquée d'un clic sur son "?", et un **résumé en langage clair** généré automatiquement en dessous du tableau. Un bouton "Comment lire ces résultats ?" donne un guide pas-à-pas pour un débutant.

### Le réflexe à prendre : ne jamais juger sur un seul test

Depuis la mise à jour du 13 août 2026, chaque résultat de test affiche aussi son **historique** : cette même stratégie est rejouée automatiquement chaque semaine, à paramètres par défaut, sur toutes les positions du portefeuille virtuel. Le taux de réussite moyen sur 90 jours et sur 12 mois s'affiche à côté du résultat du jour, avec un badge qui prévient explicitement quand l'échantillon est encore trop petit pour en tirer une conclusion (moins de 5 tests). C'est la meilleure protection contre le piège classique du débutant : se fier à un test ponctuel qui a « bien marché » par hasard, plutôt qu'à une tendance de fond mesurée dans la durée (voir aussi section 9).

**Piège à éviter** : plus on multiplie les combinaisons de paramètres à la recherche du "meilleur" résultat de backtest, plus on risque de sur-ajuster une stratégie au passé sans qu'elle marche mieux à l'avenir. Un backtest est un outil de compréhension, pas une preuve.

---

## 8. Le Labo d'analyse — comprendre sur quoi un modèle se base

Cet outil, en lecture seule (rien n'y modifie un signal officiel), sert à explorer la mécanique derrière les modèles de prédiction.

### Onglet "Par actif"

- Le **signal réel** du moteur de règles est affiché en référence.
- Plusieurs **modèles légers** (Random Forest, XGBoost, ARIMA, Prophet, et un modèle d'ensemble qui vote entre eux) sont entraînés à la volée et comparés au signal réel, avec pour chacun sa direction prédite, sa probabilité de hausse, sa précision (entraînement vs validation sur des données jamais vues), et ses facteurs les plus influents.
- Un **LSTM** (réseau de neurones séquentiel) peut être entraîné en tâche de fond — plus lent, le résultat arrive après quelques secondes.
- Un tableau liste plus de 70 **indicateurs techniques bruts** calculés pour ce titre (moyennes mobiles, oscillateurs, volumes...), chacun expliqué au survol, avec une "zone" qui situe la valeur dans sa fourchette de lecture usuelle quand elle en a une.
- Un **indicateur ajustable** : on choisit un indicateur (RSI, Bollinger, ADX, stochastique, etc.), on modifie ses paramètres (période, écarts-types...) et on le recalcule en direct, avec une explication de la formule utilisée juste en dessous — l'endroit idéal pour comprendre concrètement "comment on obtient ce chiffre".

### Onglet "Sur le portefeuille virtuel"

La même comparaison (signal réel vs modèles), mais sur toutes les positions détenues à la fois, pour repérer d'un coup d'œil les titres où les modèles sont d'accord ou non entre eux.

---

## 9. Page Fiabilité — la mémoire de l'application

C'est la page qui répond à la question « est-ce que ça marche vraiment, dans la durée ? », en deux volets.

### Fiabilité du moteur de signal

La précision **réelle** du moteur de règles sur les signaux déjà calculés et arrivés à échéance (5 jours pour le court terme, jusqu'à 60 jours pour le long terme), mise à jour automatiquement chaque jour — pas un backtest, une mesure sur ce qui s'est vraiment passé après un signal réel.

### Fiabilité des stratégies de backtest

Chaque stratégie testable dans le Labo de paramètres est rejouée automatiquement chaque semaine, à paramètres par défaut, sur les positions du portefeuille — pour voir son évolution dans la durée plutôt qu'un seul test isolé. Le tableau est **triable** par fenêtre (90 jours / 12 mois / tout l'historique), avec un rang par ligne et, pour chaque cellule, un badge indiquant si l'échantillon est encore trop petit pour juger, limité, ou plus étoffé.

**Point important** : le moteur interne et "nos signaux" varient par horizon (court/moyen/long), alors que les stratégies de référence (SMA, RSI, MACD, Bollinger, buy & hold) sont indépendantes de l'horizon — le classement reste donc indicatif, pas un verdict absolu. Toujours regarder le badge de confiance avant de comparer deux lignes entre elles.

Ces deux scorecards démarrent vides et se remplissent progressivement : c'est normal juste après l'activation de la fonctionnalité, il faut laisser le temps aux jobs planifiés de tourner plusieurs fois.

---

## 10. Suivi des actifs

Une page technique qui montre, titre par titre, la fraîcheur des données (dernier prix connu, dernier signal calculé, dernier consensus d'analystes récupéré), avec un bouton pour forcer la mise à jour d'un titre précis ou de tous les titres à la suite. Utile pour vérifier qu'un titre récemment ajouté a bien fini d'être initialisé avant de s'étonner qu'il manque de données.

---

## 11. Top achats et comparaison des prédictions

Un tableau qui met côte à côte, pour chaque titre suivi : l'avis des analystes externes (Yahoo Finance), le signal du moteur de règles interne, celui du modèle statistique, un indicateur d'accord/désaccord entre eux, et la tendance réelle sur 12 mois. Le but est de juger visuellement, au fil du temps, laquelle des sources colle le mieux à la réalité — un exercice d'esprit critique plus qu'un classement à suivre aveuglément.

---

## 12. Historique des signaux

Un graphique de l'évolution du signal d'un titre dans le temps, par horizon — pratique pour voir si un signal a changé récemment, et à quel moment.

---

## 13. Briefing quotidien

Une synthèse automatique, en français, des actualités et signaux récents sur les titres détenus et suivis — jamais un conseil, juste un résumé pour ne rien manquer. On peut y ajouter des **mots-clés personnalisés** (avec un poids et un horizon d'impact) pour que l'application les repère spécifiquement dans les prochains articles ingérés, et consulter un résumé automatique des articles qui correspondent déjà à ces mots-clés.

---

## Glossaire express

| Terme | Explication courte |
|---|---|
| **PER** | Cours de l'action divisé par le bénéfice par action — combien de fois le bénéfice annuel le marché est prêt à payer. |
| **RSI** | Oscillateur borné 0-100 qui mesure si un titre est en zone de "survente" ou de "surachat" récente. |
| **MACD** | Écart entre deux moyennes mobiles, utilisé pour repérer un changement de tendance (momentum). |
| **Bandes de Bollinger** | Une moyenne mobile entourée de deux bandes basées sur l'écart-type récent des prix — situe un cours par rapport à sa volatilité normale. |
| **ROE** | Rentabilité de l'entreprise rapportée aux capitaux apportés par les actionnaires. |
| **Drawdown (perte maximale)** | La plus grosse chute entre un sommet et un creux pendant une période testée. |
| **Ratio de Sharpe** | Rendement rapporté à la volatilité totale — mesure la qualité statistique d'un résultat, pas une prédiction. |
| **Buy & hold** | Stratégie de référence : acheter une fois et ne jamais revendre — le point de comparaison qu'une stratégie active doit nettement battre pour être utile. |
| **Backtest** | Simulation d'une stratégie sur des données passées — jamais une garantie sur l'avenir. |
| **Scorecard de fiabilité** | Le suivi, dans la durée, de la performance réelle (signaux) ou historique (stratégies de backtest) — pour arbitrer sur une tendance plutôt que sur un seul résultat. |

---

## En résumé : une méthode de travail suggérée

1. Regarder la page Marché pour prendre le pouls du jour.
2. Choisir un titre (recherche ou watchlist) et lire sa fiche : signal, fondamentaux, comparatif sectoriel.
3. Ouvrir "pourquoi ce signal ?" pour comprendre le calcul, pas juste le résultat.
4. Aller dans le Labo d'analyse pour voir sur quels indicateurs bruts ce calcul s'appuie, et comparer aux modèles statistiques.
5. Si l'idée est de tester une stratégie, utiliser le Labo de paramètres — et toujours vérifier le contexte historique affiché sous le résultat avant de conclure quoi que ce soit.
6. Consulter régulièrement la page Fiabilité pour voir si les stratégies et le moteur de signal tiennent leurs promesses dans la durée, pas seulement sur un test isolé.
7. Ne jamais oublier la règle de départ : cette application enseigne à lire des données financières et à raisonner statistiquement, elle ne remplace ni un conseiller financier, ni son propre jugement.
