# 4. Arborescence dossier par dossier

```
bourse-app/
├── README.md                          # point d'entrée : comment naviguer ce livrable
├── LEARNING_PATH.md                    # parcours pédagogique par étapes (formation)
├── docs/                               # les 17 livrables demandés, un fichier par thème
│   ├── 01-vision-produit.md
│   ├── 02-fonctionnalites-mvp-v2.md
│   ├── 03-architecture.md
│   ├── 04-arborescence.md
│   ├── 05-schema-postgresql.sql        # DDL exécutable
│   ├── 05-schema-postgresql.md         # explication du schéma
│   ├── 06-modules-python.md
│   ├── 07-endpoints-fastapi.md
│   ├── 08-pipeline-ingestion.md
│   ├── 09-strategie-nlp-sentiment.md
│   ├── 10-strategie-prevision-temporelle.md
│   ├── 11-strategie-scoring-hybride.md
│   ├── 14-jobs-planifies.md
│   ├── 16-plan-deploiement.md
│   ├── 17-limites-legales-techniques.md
│   └── risques-priorites-sources.md
│
├── backend/
│   ├── .env.example                    # variables d'environnement, jamais de secret en dur
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/                   # migrations générées (vide au départ)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # point d'entrée FastAPI, montage des routers
│   │   ├── config.py                   # Settings Pydantic (lit le .env)
│   │   ├── database.py                 # engine SQLAlchemy, session, Base declarative
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── logging.py              # config du logging structuré
│   │   │   └── exceptions.py           # exceptions métier communes + handlers FastAPI
│   │   ├── domains/
│   │   │   ├── assets/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py           # table Asset
│   │   │   │   ├── schemas.py          # AssetCreate, AssetRead...
│   │   │   │   ├── repository.py       # requêtes CRUD Asset
│   │   │   │   ├── service.py          # logique métier (recherche, filtres)
│   │   │   │   └── router.py           # /api/v1/assets
│   │   │   ├── market_data/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py           # PriceBar, TechnicalIndicator
│   │   │   │   ├── schemas.py
│   │   │   │   ├── repository.py
│   │   │   │   ├── service.py          # calcul indicateurs (SMA, RSI, MACD, volatilité)
│   │   │   │   ├── router.py           # /api/v1/market-data
│   │   │   │   └── providers/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── base.py         # interface abstraite MarketDataProvider
│   │   │   │       └── yahoo_finance.py # implémentation yfinance/httpx
│   │   │   ├── news/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py           # NewsArticle, NewsKeywordMatch
│   │   │   │   ├── schemas.py
│   │   │   │   ├── repository.py
│   │   │   │   ├── service.py          # orchestration ingestion + NLP
│   │   │   │   ├── router.py           # /api/v1/news
│   │   │   │   ├── providers/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base.py
│   │   │   │   │   └── rss_provider.py # flux RSS gratuits (Yahoo/Google News)
│   │   │   │   └── nlp/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── sentiment.py    # scoring de sentiment (lexique pondéré)
│   │   │   │       ├── keywords.py     # extraction et pondération de mots-clés
│   │   │   │       └── lexicon.py      # dictionnaires de mots-clés/poids (config)
│   │   │   ├── signals/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py           # Signal, SignalExplanation
│   │   │   │   ├── schemas.py
│   │   │   │   ├── repository.py
│   │   │   │   ├── features.py         # construction des features (temporel+news)
│   │   │   │   ├── engine.py           # moteur de score explicable (règles pondérées)
│   │   │   │   ├── service.py          # orchestration : features -> engine -> persist
│   │   │   │   ├── router.py           # /api/v1/signals
│   │   │   │   └── models_ml/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── baseline_rules.py     # V1 : règles pondérées
│   │   │   │       └── logistic_model.py     # V2 : régression logistique (comparaison)
│   │   │   ├── backtests/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py           # BacktestRun, BacktestResult
│   │   │   │   ├── schemas.py
│   │   │   │   ├── repository.py
│   │   │   │   ├── service.py          # rejeu historique, calcul métriques
│   │   │   │   └── router.py           # /api/v1/backtests
│   │   │   ├── users/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py           # User
│   │   │   │   ├── schemas.py
│   │   │   │   ├── repository.py
│   │   │   │   ├── auth.py             # hashing, JWT (V1 : simple, V2 : renforcé)
│   │   │   │   ├── service.py
│   │   │   │   └── router.py           # /api/v1/auth
│   │   │   └── compliance/
│   │   │       ├── __init__.py
│   │   │       ├── disclaimers.py      # textes légaux centralisés
│   │   │       └── guardrails.py       # validation du vocabulaire des signaux
│   │   └── jobs/
│   │       ├── __init__.py
│   │       ├── scheduler.py            # configuration APScheduler
│   │       ├── ingest_prices_job.py
│   │       ├── ingest_news_job.py
│   │       └── compute_signals_job.py
│   └── tests/
│       ├── conftest.py                 # fixtures (DB de test, client FastAPI)
│       ├── test_assets_api.py
│       ├── test_market_data_indicators.py
│       ├── test_news_sentiment.py
│       ├── test_signals_engine.py
│       └── test_backtests_metrics.py
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue
        ├── api/
        │   └── client.js               # wrapper axios/fetch vers l'API FastAPI
        ├── router/
        │   └── index.js
        ├── stores/
        │   ├── assets.js                # Pinia store
        │   └── signals.js
        ├── views/
        │   ├── DashboardView.vue
        │   ├── AssetSearchView.vue
        │   └── SignalHistoryView.vue
        └── components/
            ├── SignalCard.vue           # score + explication + niveau de confiance
            ├── TrendChart.vue           # graphique prix/volume
            └── HorizonTabs.vue          # court/moyen/long terme
```

## Convention de nommage
- Domaines métier en anglais (`assets`, `signals`...) pour rester cohérent avec l'écosystème Python/FastAPI, mais toute la documentation et les textes utilisateur restent en français.
- Fichiers Python en `snake_case`, classes en `PascalCase`, endpoints REST en `kebab-case` (`/market-data`, pas `/market_data`).
- Un seul point d'entrée logique par domaine : `router.py` — jamais de logique dispersée dans `main.py`.
