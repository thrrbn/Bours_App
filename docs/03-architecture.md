# 3. Architecture complète

## Choix structurant : monolithe modulaire, pas de microservices

**Pourquoi c'est le bon choix pour un développeur solo :**
- Un seul processus à déployer, un seul repo à faire évoluer, un seul schéma de base à migrer (Alembic linéaire).
- Le débogage reste local : pas de traçage distribué, pas de gestion de la latence réseau inter-services, pas de gestion de la cohérence entre bases de données séparées.
- Le découpage par **domaine métier** (et non par couche technique) donne déjà les bénéfices de la modularité (bas couplage, tests isolés, remplaçabilité d'un module) sans le coût opérationnel des microservices (CI/CD multiplié, observabilité distribuée, orchestration).
- Un microservice ne se justifie que quand une équipe séparée doit déployer indépendamment, ou qu'un composant a un profil de charge radicalement différent du reste. Aucun des deux cas ne s'applique ici : c'est un seul développeur, un trafic faible à modéré (usage personnel/niche), et les composants (ingestion, NLP, scoring) partagent le même cycle de vie de données.
- Migration future : si un jour un domaine (ex. NLP) a besoin d'une charge de calcul isolée (GPU dédié), il pourra être extrait en service séparé **sans réécrire le reste**, précisément parce que le découpage par domaine existe déjà en interne.

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3 SPA)                     │
│         Vite + Pinia + Vue Router + Tailwind CSS                │
└───────────────────────────────┬───────────────────────────────--┘
                                 │ HTTPS / JSON (REST)
┌────────────────────────────── ▼ ──────────────────────────────--┐
│                     API FastAPI (monolithe modulaire)            │
│                                                                    │
│  ┌───────────┐ ┌─────────────┐ ┌─────────┐ ┌─────────┐          │
│  │  assets   │ │ market_data │ │  news   │ │ signals │          │
│  └───────────┘ └─────────────┘ └─────────┘ └─────────┘          │
│  ┌───────────┐ ┌─────────────┐ ┌─────────┐                      │
│  │ backtests │ │    users    │ │compliance│                     │
│  └───────────┘ └─────────────┘ └─────────┘                      │
│                                                                    │
│  Chaque domaine : router.py (endpoints) / service.py (logique)   │
│  repository.py (accès données) / models.py (ORM) / schemas.py    │
│  (Pydantic, contrat API)                                          │
└──────────┬────────────────────────────────────┬──────────────---─┘
           │                                    │
┌──────────▼──────────┐              ┌──────────▼──────────────---─┐
│   PostgreSQL         │              │   Jobs planifiés (APScheduler)│
│   (données de marché,│              │   - ingestion prix quotidienne│
│   news, signaux,     │              │   - ingestion news périodique │
│   utilisateurs)      │              │   - calcul des signaux        │
└──────────────────────┘              └────────────────────────────--┘
           ▲
           │
┌──────────┴──────────────────────────────────────────────────---──┐
│           Fournisseurs externes (httpx, async)                    │
│   Yahoo Finance (yfinance / scraping léger) · Flux RSS financiers │
│   Benzinga (V2, si budget) · Sources belges (V2)                  │
└────────────────────────────────────────────────────────────────---┘
```

## Découpage par domaine (bounded contexts internes)

| Domaine | Responsabilité | Dépend de |
|---|---|---|
| `assets` | Référentiel des actifs suivis (ticker, marché, secteur, devise, métadonnées) | rien (domaine racine) |
| `market_data` | Ingestion et stockage des prix/volumes, calcul des indicateurs techniques | `assets` |
| `news` | Ingestion des actualités, NLP (sentiment, mots-clés), impact par horizon | `assets` |
| `signals` | Moteur de score : combine `market_data` + `news` en signal explicable | `assets`, `market_data`, `news` |
| `backtests` | Rejoue les signaux passés, calcule les métriques de performance | `signals` |
| `users` | Comptes, authentification, watchlists | rien (domaine racine) |
| `compliance` | Disclaimers, garde-fous de formulation, journal d'audit | transverse (utilisé par `signals`) |

Chaque domaine expose son propre `router.py` monté sur `main.py` avec un préfixe (`/api/v1/assets`, `/api/v1/signals`...). La communication entre domaines se fait **par appel de fonction Python direct** (service à service, dans le même process), jamais par HTTP interne : c'est l'un des principaux gains du monolithe.

## Couches à l'intérieur d'un domaine

```
domains/signals/
├── models.py        # tables SQLAlchemy (persistance)
├── schemas.py        # schémas Pydantic (contrat API, entrée/sortie)
├── repository.py    # requêtes SQL/ORM pures, pas de logique métier
├── service.py         # logique métier : orchestration, calculs, règles
├── engine.py         # moteur de scoring (cœur explicable, testé isolément)
└── router.py           # endpoints FastAPI, appelle service.py uniquement
```

Règle stricte : `router.py` ne contient **jamais** de logique métier (uniquement validation d'entrée + appel service + formatage de sortie). Cela permet de tester `service.py` et `engine.py` unitairement sans lancer de serveur HTTP, et de réutiliser cette logique depuis un job planifié (`jobs/`) sans dupliquer de code.

## Asynchrone : où et pourquoi

- **Endpoints FastAPI** : `async def` partout où l'on fait des appels réseau (fournisseurs externes) ou des requêtes DB, pour ne pas bloquer le worker sur les I/O — gain réel même en solo car un seul utilisateur peut avoir plusieurs onglets/requêtes simultanées, et les jobs planifiés tournent en parallèle des requêtes API.
- **Ingestion de données** (`httpx.AsyncClient`) : requêtes vers Yahoo Finance/RSS en asynchrone pour paralléliser l'ingestion de plusieurs tickers sans multiplier les threads.
- **Calcul du score et NLP** : restent **synchrones** (CPU-bound, pandas/numpy/scikit-learn ne sont pas async par nature). Ils tournent dans les jobs planifiés (hors du cycle requête/réponse HTTP), donc ne bloquent jamais un utilisateur qui consulte le dashboard.
- **Pas de Celery en V1** : APScheduler intégré au process FastAPI suffit largement pour quelques jobs quotidiens sur une dizaine à quelques centaines d'actifs. Celery + Redis n'apporte de valeur qu'à partir du moment où (a) plusieurs workers doivent tourner sur des machines séparées, ou (b) le volume de tâches dépasse ce qu'un scheduler in-process peut absorber. Aucun des deux n'est vrai en V1 — décision réévaluée en V2 seulement si mesurée nécessaire (voir doc 14).

## Frontend : Vue 3 + Vite + Pinia + Tailwind

- **Vite** : démarrage instantané, build rapide, adapté à un solo dev qui itère vite.
- **Pinia** : state management officiel Vue 3, remplace Vuex, API simple (stores par domaine : `useAssetsStore`, `useSignalsStore`).
- **Tailwind CSS** : permet de construire une UI propre sans maintenir un design system séparé — pertinent pour un solo dev qui doit aussi faire le design.
- **Vue Router** : navigation SPA classique (dashboard, recherche, historique).
- Communication avec le backend en REST/JSON uniquement (pas de GraphQL — complexité non justifiée pour ce périmètre).

## Intégration future à un stack de référence
Le découpage strict domaine/couche (routers/services/repositories, schémas Pydantic comme contrat d'API stable) est ce qui rend l'intégration future la plus simple : n'importe quel système externe peut consommer l'API REST versionnée (`/api/v1/...`) sans connaître les détails internes. Si le stack de référence évolue (ex. passage à un autre frontend, exposition à un autre système backend), c'est la couche `schemas.py` (contrat Pydantic) qui sert de point de stabilité — elle ne doit pas changer sans versionnement explicite (`/api/v2/...`).
