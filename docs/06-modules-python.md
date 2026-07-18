# 6. Modules Python à créer

Liste des modules avec leur responsabilité unique (Single Responsibility). Le code correspondant est dans `backend/app/` (voir doc 12 pour le code de base).

## `app/config.py`
Une classe `Settings(BaseSettings)` (Pydantic) qui lit toutes les variables d'environnement (`.env`) : URL de base de données, clés API externes, secret JWT, environnement (dev/prod). Jamais de valeur en dur ailleurs dans le code.

## `app/database.py`
Création de l'engine SQLAlchemy (async, `create_async_engine`), de la session factory, et de la `Base` declarative dont héritent tous les modèles. Fournit une dépendance FastAPI `get_db()` injectée dans les routers.

## `app/core/logging.py`
Configuration d'un logger structuré (format JSON en production, lisible en dev). Chaque job et chaque appel à un fournisseur externe logue son résultat (succès/échec, durée, volume de données).

## `app/core/exceptions.py`
Exceptions métier (`AssetNotFoundError`, `DataProviderError`, `InsufficientDataError`) et leurs handlers FastAPI associés (conversion en réponses HTTP propres avec code et message clair).

## `domains/assets/`
- `models.py` : `Asset` (SQLAlchemy).
- `schemas.py` : `AssetCreate`, `AssetRead`, `AssetSearchResult`.
- `repository.py` : `get_by_ticker`, `search`, `list_by_sector`, `create`.
- `service.py` : logique de recherche (normalisation ticker, résolution du marché), pas d'accès SQL direct.
- `router.py` : `GET /assets`, `GET /assets/{id}`, `GET /assets/search`.

## `domains/market_data/`
- `models.py` : `PriceBar`, `TechnicalIndicator`.
- `providers/base.py` : interface abstraite `MarketDataProvider.fetch_history(ticker, start, end) -> list[PriceBarDTO]`. Permet de changer de fournisseur (Yahoo → autre) sans toucher au reste du domaine.
- `providers/yahoo_finance.py` : implémentation concrète (via `yfinance` ou `httpx` direct sur l'endpoint non officiel), avec gestion des erreurs et des limites de débit.
- `service.py` : `ingest_history(asset)`, `compute_indicators(asset, as_of_date)` — calculs pandas/numpy (SMA, EMA, RSI, MACD, Bollinger, volatilité, momentum).
- `repository.py` : upsert idempotent des `PriceBar`/`TechnicalIndicator`.
- `router.py` : `GET /market-data/{asset_id}/prices`, `GET /market-data/{asset_id}/indicators`.

## `domains/news/`
- `models.py` : `NewsArticle`, `NewsKeywordMatch`.
- `providers/rss_provider.py` : parsing de flux RSS (Yahoo Finance RSS, Google News RSS filtré par ticker), déduplication par URL.
- `nlp/lexicon.py` : dictionnaire configuré `{mot_cle: {poids, horizon_impact}}` (achat, acquisition, restructuration, licenciement, guidance, profit warning, croissance, dette, fusion, dilution...).
- `nlp/sentiment.py` : `score_sentiment(text) -> float` — approche lexicon-based en V1 (voir doc 09), interchangeable avec un modèle pré-entraîné.
- `nlp/keywords.py` : `extract_keywords(text) -> list[KeywordMatch]` — matching + comptage + résolution de l'horizon d'impact dominant.
- `service.py` : orchestration ingestion → NLP → persistance.
- `router.py` : `GET /news/{asset_id}`, `GET /news/{asset_id}/sentiment-summary`.

## `domains/signals/`
- `features.py` : `build_feature_vector(asset, as_of_date) -> SignalFeatures` — agrège les indicateurs techniques et le résumé news en un seul objet structuré, entrée unique du moteur de score.
- `models_ml/baseline_rules.py` : moteur de règles pondérées (V1), fonction pure `compute(features: SignalFeatures) -> SignalResult`.
- `models_ml/logistic_model.py` : squelette de modèle de régression logistique (V2), même contrat d'entrée/sortie que `baseline_rules.py` pour comparaison directe (voir doc 11).
- `engine.py` : sélectionne le modèle actif (config), appelle `compute()`, construit l'explication textuelle par template.
- `service.py` : orchestre `features.py` + `engine.py`, persiste `Signal` + `SignalExplanation`.
- `router.py` : `GET /signals/{asset_id}`, `GET /signals/{asset_id}/history`.

## `domains/backtests/`
- `service.py` : rejoue les signaux historiques stockés (`Signal`) contre les prix réels ultérieurs (`PriceBar`), calcule précision/win rate/drawdown/faux positifs.
- `router.py` : `POST /backtests/run`, `GET /backtests/{id}`.

## `domains/users/`
- `auth.py` : hashing (`passlib`/`bcrypt`), génération/validation JWT (`python-jose`).
- `service.py`, `router.py` : `POST /auth/register`, `POST /auth/login`, `GET /auth/me`. (V1 : un seul compte admin local suffit ; l'architecture supporte déjà le multi-utilisateur pour la V2.)

## `domains/compliance/`
- `disclaimers.py` : textes légaux centralisés (une seule source de vérité, réutilisée par le frontend via l'API pour éviter toute divergence de formulation).
- `guardrails.py` : fonction `validate_signal_wording(text) -> None` qui lève une erreur si un texte généré contient un vocabulaire interdit ("garanti", "certain", "conseil personnalisé"...) — filet de sécurité automatisé sur la génération de texte.

## `app/jobs/`
- `scheduler.py` : instancie l'`AsyncIOScheduler` d'APScheduler au démarrage de l'application (hook `lifespan` FastAPI).
- `ingest_prices_job.py`, `ingest_news_job.py`, `compute_signals_job.py` : fonctions appelées par le scheduler, qui réutilisent exactement les `service.py` de chaque domaine (aucune logique dupliquée entre API et jobs).
