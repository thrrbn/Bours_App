# 2. Fonctionnalités MVP vs V2

## Principe de découpage
Le MVP doit être **réellement livrable et utile seul**, pas une coquille vide. Le critère retenu : un MVP qui permet de suivre 5 à 10 actifs (actions belges/européennes + quelques US) avec un signal explicable, mis à jour quotidiennement, et un historique consultable. Tout ce qui relève de la sophistication du modèle, du multi-utilisateur, ou de l'automatisation avancée est repoussé en V2.

## MVP (V1) — livrable en solo en 8 à 12 semaines à temps partiel

### Données
- Ingestion des prix et volumes historiques + quotidiens via Yahoo Finance (librairie `yfinance` ou scraping léger via `httpx`).
- Calcul d'indicateurs techniques de base : moyennes mobiles (SMA/EMA), RSI, MACD, volatilité (écart-type glissant), Bollinger Bands.
- Ingestion d'actualités financières via un flux RSS gratuit (Yahoo Finance RSS, Google News RSS filtré par ticker) — pas encore Benzinga (payant, V2 si le budget le permet).
- Métadonnées actif : ticker, nom, marché (Euronext Brussels, NYSE, NASDAQ...), secteur, devise.

### Analyse temporelle
- Détection de tendance court terme (5-20 jours), moyen terme (1-3 mois), long terme (6-12 mois) par régression linéaire glissante + croisement de moyennes mobiles.
- Détection de rupture simple (changement de régime de volatilité, franchissement de bande de Bollinger).
- Calcul de momentum (ROC, RSI) et de volatilité réalisée.

### NLP / News
- Scoring de sentiment par lexique financier pondéré (pas de modèle deep learning en V1 — voir doc 09) + un modèle pré-entraîné léger de secours (FinBERT via `transformers`, optionnel si les ressources CPU le permettent).
- Extraction de mots-clés à impact (liste pondérée : achat, acquisition, restructuration, licenciement, guidance, profit warning, croissance, dette, fusion, dilution...).
- Association d'un impact d'horizon (court/moyen/long) par mot-clé, codé en dur dans une table de configuration (pas encore apprise).

### Moteur de score
- Score technique (0-100), score news (0-100), score de risque (0-100, basé sur volatilité + dette si disponible), score de confiance (basé sur la quantité et la fraîcheur des données disponibles).
- Signal final par règles pondérées explicites (pas de boîte noire) : achat spéculatif / surveillance / neutre / prudence / vente défensive.
- Explication textuelle générée par template (pas de LLM en V1, génération déterministe à partir des composantes du score — voir doc 11).

### Interface (Vue.js)
- Recherche d'un actif (par ticker ou nom).
- Dashboard d'un actif : score actuel par horizon, graphique prix/volume, explication du signal.
- Historique des signaux (table + petit graphique d'évolution du score dans le temps).
- Filtre par marché (Euronext Brussels / US / Europe) et par secteur.

### Backtesting
- Rejouer les signaux historiques générés par le moteur de règles sur les données passées.
- Afficher précision (le signal a-t-il anticipé le bon sens de mouvement), taux de faux positifs, drawdown maximum sur la période suivant le signal.

### Gouvernance du risque
- Bandeau de disclaimer permanent, non masquable, sur chaque écran de signal.
- Toujours afficher le score de confiance à côté du signal (jamais un signal seul).
- Journal d'audit : chaque signal stocké avec sa version de règles/modèle (traçabilité).

### Infra
- Fonctionne en local (Docker Compose : API FastAPI + PostgreSQL), un seul utilisateur (pas d'authentification multi-utilisateur en V1 — un compte admin unique suffit).
- Jobs planifiés via APScheduler (pas Celery — inutile en V1, voir doc 14).

## V2 — après validation du MVP par l'usage réel

### Données
- Intégration Benzinga (si plan abordable confirmé) pour des news qualifiées et un flux plus riche (analyste ratings, earnings calendar).
- Ajout de sources belges spécifiques (communiqués Euronext Brussels, presse financière belge : L'Echo, De Tijd — si API/flux disponible).
- Ajout de fondamentaux (ratios P/E, dette/capitaux propres) via une source dédiée.

### Analyse temporelle
- Détection de rupture plus robuste (changement de régime via un modèle de type CUSUM ou Bayesian change point detection).
- Modèles de séries temporelles simples (ARIMA/ETS) en complément des règles, pour comparaison (voir doc 10).

### NLP
- Modèle de sentiment fine-tuné sur du vocabulaire financier français/anglais si volume de données suffisant.
- Détection d'entités nommées (quelle société est concernée précisément dans l'article) pour réduire le bruit du matching par mot-clé simple.

### Scoring
- Remplacement progressif des règles pondérées par un modèle de gradient boosting (LightGBM/XGBoost) entraîné sur l'historique de backtesting, **en gardant les règles comme baseline de comparaison et comme filet de secours explicable**.
- Calibration de probabilité (Platt scaling / isotonic regression) pour que le score de confiance soit statistiquement fondé, pas seulement heuristique.

### Interface
- Multi-utilisateur avec authentification (JWT), comptes et watchlists personnelles.
- Notifications (email) sur changement de signal pour les actifs suivis.
- Vue portefeuille agrégée (plusieurs actifs, score de risque global).

### Backtesting
- Comparaison de plusieurs versions de moteur de score en parallèle (A/B historique).
- Rapport de performance exportable (PDF).

### Infra
- Déploiement production (VPS européen, cf. doc 16), migration éventuelle vers Celery + Redis si le volume de jobs le justifie réellement (pas avant d'en avoir la preuve par la mesure).
- Observabilité (logs structurés, métriques Prometheus/Grafana basiques).

## Ce qui reste explicitement hors scope, même en V2
- Aucun passage d'ordre automatique ou semi-automatique.
- Aucune gestion de portefeuille réel (custody), l'application reste un outil d'analyse, jamais un courtier.
- Aucun contenu présenté comme un conseil personnalisé au sens réglementaire.
