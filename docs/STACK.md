# Stack technique — Bourse Assistant

Document vivant : mis à jour à chaque session de développement (nouvelle dépendance, domaine ajouté, dette technique corrigée ou identifiée). Ne remplace pas `docs/03-architecture.md` (les choix et leur justification) ni `LEARNING_PATH.md` (le parcours pédagogique) : c'est l'état des lieux factuel, à consulter en premier pour savoir « qu'est-ce qui existe déjà et comment ça marche ».

Dernière mise à jour : **30/07/2026**.

## Vue d'ensemble

Application d'analyse boursière à usage personnel (un seul utilisateur réel visé en V1, voir `docs/17-limites-legales-techniques.md`) : ingestion de prix et de news pour un univers d'actifs seedable à la demande (BEL20, CAC40, DAX40, AEX, megacaps US, panier crypto Binance — voir « Univers d'actifs » ci-dessous), calcul d'un signal explicable par un moteur de règles pondérées, portefeuille virtuel de simulation, backtesting, notifications par email.

```
bourse-app/
├── backend/     FastAPI + SQLAlchemy async + APScheduler (Python 3.12)
├── frontend/    Vue 3 + Vite + Pinia + Tailwind
├── db/          Bootstrap SQL (docker-entrypoint-initdb.d)
├── docs/        17 livrables de conception + ce document
└── docker-compose.yml
```

## Stack technique

| Couche | Techno | Version épinglée | Notes |
|---|---|---|---|
| Backend runtime | Python | 3.12 (image `python:3.12-slim`) | sandbox de dev/CI actuel tourne en 3.10, sans incidence (aucune syntaxe 3.12-only utilisée) |
| Framework API | FastAPI | `>=0.115` | non figé à l'exact — `pip install` récupère la dernière mineure compatible |
| ORM | SQLAlchemy | `>=2.0`, mode async (`asyncpg`) | |
| Migrations | Alembic | `>=1.13` | **remis en état de marche le 25/07/2026**, voir section dédiée |
| Base de données | PostgreSQL | 18 (image officielle, `docker-compose.yml`) | |
| Scheduler | APScheduler | `>=3.10` | jobs in-process, pas de worker séparé (voir docs/14) |
| Auth | python-jose + passlib(bcrypt) | | domaine `users` présent, **non branché** sur les autres routes (voir Gaps) |
| Data science | pandas, numpy, scikit-learn | | indicateurs techniques + modèle ML optionnel (`signals/models_ml/logistic_model.py`) |
| Ingestion prix (actions/ETF) | yfinance | `>=0.2.40` | non officiel, voir risque #1 dans `docs/risques-priorites-sources.md` |
| Ingestion prix (crypto) | API publique Binance (`/api/v3/klines`) | via `httpx` (déjà en dépendance) | **ajouté le 30/07/2026** — lecture seule, aucune clé API, aucun ordre. Actifs `market="BINANCE"` uniquement (voir `market_data/providers/binance.py`) |
| Ingestion news | feedparser (RSS) | | |
| Email | aiosmtplib | | digest unique, désactivé par défaut (`MAIL_ENABLED=false`) |
| Tests backend | pytest, pytest-asyncio | | 44 tests, tous unitaires/purs (pas de DB requise, voir `tests/conftest.py`) |
| Frontend framework | Vue | `^3.4` | Composition API |
| Build frontend | Vite | `^5.2` | |
| State management | Pinia | `^2.1.7` | 7 stores, un par domaine consommé |
| Styles | Tailwind CSS | `^3.4` | |
| Graphiques | Chart.js + vue-chartjs | `^4.4` / `^5.3` | |
| HTTP client | Axios | `^1.7` | |
| Conteneurisation | Docker Compose | services : `db`, `pgadmin`, `backend`, `frontend` | |

## Architecture backend

Découpage par domaine (`backend/app/domains/<domaine>/`), chaque domaine suivant le même pattern en couches : `models.py` (SQLAlchemy) → `schemas.py` (Pydantic) → `repository.py` (requêtes pures) → `service.py` (logique métier) → `router.py` (HTTP, zéro logique). ~4 300 lignes de Python applicatif (hors tests/migrations).

12 domaines dans `backend/app/domains/` (11 annoncés avant cette mise à jour — décompte corrigé le 30/07/2026, `maintenance` avait été omis) :

| Domaine | Modèle(s) ORM | Rôle |
|---|---|---|
| `assets` | `Asset` | CRUD actifs, recherche. Seed statique BEL20 (`seed_data.py`) et Binance majors (`seed_data_binance.py`), tous deux idempotents (`repository.bulk_upsert`, `ON CONFLICT DO NOTHING`) |
| `market_data` | `PriceBar`, `TechnicalIndicator` | ingestion Yahoo Finance (actions/ETF) ou Binance (crypto, `market="BINANCE"` — API publique `/api/v3/klines`, sans clé, lecture seule), indicateurs (SMA/EMA/RSI/MACD/Bollinger/volatilité). Provider choisi par `market_data.service.provider_for_market()` selon `Asset.market` ; chaque `price_bar` trace sa provenance (`source="yahoo_finance"` / `"binance"`) |
| `news` | `NewsArticle`, `NewsKeywordMatch` | ingestion RSS, scoring de sentiment lexical (sans ML) |
| `signals` | `Signal`, `SignalExplanation` | moteur de score par règles pondérées, explication textuelle systématique |
| `backtests` | `BacktestRun`, `BacktestResult` | walk-forward, métriques (précision, win rate, drawdown, Sharpe, Calmar...) |
| `compliance` | *(aucun — voir Gaps)* | garde-fous de formulation (`validate_signal_wording`), disclaimer |
| `watchlist` | `WatchlistItem` | suivi d'actifs avec notification optionnelle |
| `notifications` | `NotificationState` | détection de changement de signal, digest email unique |
| `portfolio` | `PortfolioState`, `PortfolioPosition`, `PortfolioTransaction` | simulation d'achat/vente, frais + slippage |
| `analyst` | `AnalystConsensus` | consensus analystes externes (Yahoo), jamais fusionné à nos signaux |
| `users` | `User` | inscription/connexion JWT — **domaine orphelin**, voir Gaps |
| `maintenance` | *(aucun)* | endpoints manuels : `/refresh-all` (orchestre tous les jobs planifiés), `/seed-bel20`, `/seed-cac40`, `/seed-dax40`, `/seed-aex`, `/seed-us-majors`, `/seed-binance-majors`, `/seed-everything` (peuplent `assets` — nécessaire car `alembic upgrade head` ne crée que le schéma, jamais de données, voir sections Base de données et Univers d'actifs) |

**API** : 43 endpoints montés sous `/api/v1/*` (vérifié par introspection du schéma OpenAPI le 30/07/2026, `app.openapi()['paths']`). Détail dans `docs/07-endpoints-fastapi.md` (à recompter si ce document dérive à nouveau — c'était le cas avant la mise à jour du 25/07/2026 : il annonçait 16).

**Jobs planifiés** (`app/jobs/`, enregistrés dans `scheduler.py` au démarrage) : `ingest_prices_job` (route désormais Yahoo Finance ou Binance selon l'actif, voir `market_data`), `ingest_news_job`, `compute_signals_job`, `notify_changes_job`, `refresh_analyst_ratings_job`.

## Univers d'actifs (seed)

Aucun de ces paniers n'est seedé automatiquement (voir « piège » dans la section Base de données ci-dessous) — à peupler explicitement via les endpoints `POST /api/v1/maintenance/seed-*`, tous idempotents (rejouables sans risque de doublon). Listes statiques dans `backend/app/domains/assets/seed_data*.py`, à corriger soi-même si une composition d'indice change ou si un ticker devient invalide (silencieux : 0 barre ingérée, pas d'erreur bloquante — se voit dans la réponse de `/market-data/refresh-all`).

| Panier | Endpoint | Actifs | Marché(s) | Provider prix |
|---|---|---|---|---|
| BEL20 | `/seed-bel20` | 20 | `EURONEXT_BRUSSELS` | Yahoo Finance |
| CAC 40 | `/seed-cac40` | 39 | `EURONEXT_PARIS` | Yahoo Finance |
| DAX 40 | `/seed-dax40` | 39 | `XETRA` | Yahoo Finance |
| AEX | `/seed-aex` | 25 | `EURONEXT_AMSTERDAM` | Yahoo Finance |
| Megacaps US | `/seed-us-majors` | 34 | `NASDAQ` / `NYSE` | Yahoo Finance |
| Crypto majors | `/seed-binance-majors` | 32 | `BINANCE` | API publique Binance (sans clé) |
| **Tout à la fois** | `/seed-everything` | **~189** | — | — |

Notes : Airbus (CAC40/DAX) et ArcelorMittal (CAC40/AEX) sont dual-listés dans la réalité mais volontairement seedés une seule fois chacun (voir commentaires dans `seed_data_cac40.py`/`seed_data_dax.py`/`seed_data_aex.py`) pour éviter un doublon de ticker et une ingestion/calcul de signal redondants. Composition des indices vérifiée par recherche web le 30/07/2026 (CAC40 via zonebourse.com, DAX40 et AEX via Wikipedia/dax-indices.com/live.euronext.com) — dates de fraîcheur détaillées en tête de chaque fichier `seed_data_*.py`.

`POST /api/v1/maintenance/seed-everything` peuple `assets` mais n'ingère aucun prix — enchaîner avec `POST /api/v1/market-data/refresh-all`, qui pour ~189 actifs peut prendre plusieurs minutes (Yahoo Finance reste séquentiel pour éviter les 429, voir docs/17).

## Découverte de candidats (`GET /api/v1/assets/discover-candidates`)

Ajouté le 30/07/2026, en réponse à une demande explicite de repérer des titres à suivre à partir de l'actualité — recadrée volontairement : **jamais un ajout automatique**, uniquement une liste de suggestions factuelles que l'utilisateur valide lui-même via `POST /api/v1/assets`. Chasser le buzz médiatique pour ajouter des titres serait un biais classique (momentum/hype chasing) et se rapprocherait dangereusement d'un conseil en investissement — contraire à la philosophie du projet (`docs/17`, domaine `compliance`).

Deux sources combinées (`assets/discovery.py`) :
1. **Screener Yahoo Finance intégré à yfinance** (`yf.screen("most_actives", count=...)`) — réutilise la même négociation cookie/crumb que `market_data/providers/yahoo_finance.py` pour l'historique de prix, plutôt que d'appeler à la main les endpoints non officiels `/v1/finance/trending` et `/v7/finance/quote` (essayé en premier, rejeté par Yahoo en 403 — protection anti-bot, voir historique ci-dessous).
2. **Flux RSS + scoring de sentiment déjà en place** (`news/providers/rss_provider.py`, `news/nlp/sentiment.py`) — réutilisés tels quels sur chaque candidat, sans rien persister en base (ce n'est pas encore un actif suivi).

**Non vérifié en conditions réelles** : le sandbox de développement utilisé pour écrire cette fonctionnalité a un accès réseau sortant restreint (proxy qui bloque les requêtes vers l'API Yahoo, y compris celles de `yfinance` lui-même) — impossible d'y confirmer que `yf.screen(...)` fonctionne de bout en bout. À tester en priorité après déploiement (`curl http://localhost:8001/api/v1/assets/discover-candidates`). Point d'attention supplémentaire : `yf.screen`/`PREDEFINED_SCREENER_QUERIES` n'existent que dans des versions relativement récentes de `yfinance` (bien après la borne `>=0.2.40` de `requirements.txt`) — si `AttributeError: module 'yfinance' has no attribute 'screen'`, il faut reconstruire l'image backend (`docker compose build --no-cache backend`) pour récupérer une version à jour.

## Frontend

8 vues (`src/views/`), toutes routées dans `src/router/index.js` : recherche d'actif, dashboard/signal, historique des signaux, watchlist, portefeuille virtuel, top achats, **suivi des actifs** (ajouté le 30/07/2026 - `AssetStatusView.vue`). 8 stores Pinia, un par domaine backend consommé (`assets`, `marketData`, `signals`, `watchlist`, `portfolio`, `analyst`, `maintenance`, **`assetStatus`**). ~1 620 lignes.

**Suivi des actifs (`/status`)** : rafraîchissement titre par titre avec progression visible, plutôt qu'un bouton global qui tourne plusieurs minutes sans retour (le bouton "Tout rafraîchir maintenant" existant dans `App.vue` reste disponible, inchangé). N'introduit aucun nouveau job/streaming côté backend : `assetStatus.js` boucle côté client sur les endpoints par actif déjà existants (`POST /market-data/{id}/refresh`, `/signals/{id}/recompute`, `/analyst/{id}/refresh`), alimentée par le nouvel endpoint `GET /api/v1/assets/status` (agrégation en 4 requêtes groupées - `assets/service.py:get_status_overview` - au lieu d'une requête par actif, même principe anti-N+1 que le correctif `get_comparison_table` ci-dessus).

Pas de store/vue pour `users` (login/register) : cohérent avec le positionnement « usage strictement personnel » de la V1 (voir `docs/risques-priorites-sources.md`, priorité #10), mais à garder en tête si le projet s'ouvre un jour à plusieurs utilisateurs — l'API existe déjà côté backend, il ne manque que le câblage frontend.

## Base de données et migrations

Deux mécanismes coexistent, avec un partage des responsabilités désormais explicite :

1. **`db/migrations/001_init.sql` → `007_backtest_metrics.sql`** (319 lignes) : montés dans `docker-entrypoint-initdb.d`, exécutés une seule fois, uniquement si le volume Docker est vide. C'est le bootstrap réel utilisé par `docker-compose up`. Ne pas ajouter de nouveau fichier ici pour une évolution de schéma (voir point 2).
2. **Alembic** (`backend/alembic/`) : censé prendre le relais pour toute évolution *après* le bootstrap initial (commentaire déjà présent dans `docker-compose.yml`), mais **ne fonctionnait pas du tout avant le 25/07/2026** :
   - `alembic/script.py.mako` (template de génération de révision) était absent — `alembic revision` plantait immédiatement.
   - `alembic/env.py` n'importait que 6 domaines sur 11 dans `target_metadata` (`assets`, `backtests`, `market_data`, `news`, `signals`, `users`) — un `--autogenerate` aurait silencieusement ignoré `analyst`, `notifications`, `portfolio`, `watchlist`.
   - `alembic/versions/` était vide : aucune révision n'existait, donc `alembic upgrade head` (documenté dans le README comme étape de démarrage) n'avait jamais rien à appliquer.

   **Corrigé** : template restauré, imports complétés, révision `0001_baseline_schema` générée par autogenerate puis vérifiée (`upgrade head` et `downgrade base` testés sur un Postgres 16 jetable via `pgserver`, en dehors de Docker). Les 16 tables métier obtenues par Alembic correspondent exactement à celles créées par les SQL bruts — seule différence volontaire : les UUID sont générés côté Python (`default=uuid.uuid4`) plutôt que côté base (`uuid_generate_v4()`), donc l'extension `uuid-ossp` n'est plus nécessaire pour une base qui démarre depuis Alembic.

   À partir de maintenant : toute nouvelle colonne/table doit passer par `alembic revision --autogenerate` (après avoir bien ajouté l'import du nouveau modèle dans `env.py` si nouveau domaine), pas par un nouveau fichier SQL dans `db/migrations/`.

   **Piège identifié le 30/07/2026** : Alembic ne migre que le *schéma*, jamais les *données*. Le seed BEL20 (`db/migrations/004_bel20_seed.sql`) ne s'exécute que via `docker-entrypoint-initdb.d`, donc uniquement sur un volume Postgres vierge — une base initialisée via `alembic upgrade head` se retrouve avec une table `assets` vide (symptôme observé : l'app ne trouve aucun actif). Solution retenue : un équivalent Python idempotent (`assets/seed_data.py` + `POST /api/v1/maintenance/seed-bel20`), rejouable sans risque, indépendant du chemin de migration utilisé. Même traitement appliqué au panier crypto (`seed_data_binance.py` + `/seed-binance-majors`).

**Table orpheline détectée** : `compliance_audit_log` (créée dans `001_init.sql`) n'a aucun modèle SQLAlchemy et n'est ni lue ni écrite par le code actuel (recherche exhaustive sur `app/`). Elle existe dans le schéma mais n'est reliée à aucune fonctionnalité — voir Gaps.

## Tests et vérification

- `pytest backend/tests/ -v` → **56 tests, tous passants**, aucun ne nécessite de base de données réelle (modules purs : moteur de score, NLP, indicateurs, backtesting, garde-fous, split train/validation, prix ajustés, modèle ML, parsing des klines Binance + sélection de provider, cohérence des listes de seed, parsing du screener Yahoo Finance — `tests/test_binance_provider.py`, `tests/test_seed_data.py`, `tests/test_discovery.py`, ajoutés le 30/07/2026).
- `python -c "from app.main import app"` s'importe sans erreur, scheduler enregistré, 45 routes exposées (`app.openapi()['paths']`).
- `npm run build` (frontend) → compile sans erreur (106 modules), vérifié après l'ajout de la vue "Suivi des actifs".
- Migrations Alembic vérifiées sur un Postgres jetable (`pgserver`, sans Docker) : upgrade + downgrade propres.
- Frontend non testé automatiquement (pas de suite de tests JS dans ce dépôt) — vérification manuelle uniquement (`npm run dev`).

## Notes d'exploitation (Docker)

- **Ports** : côté host, le backend est joignable sur **8001** (`docker-compose.yml` : `"8001:8000"`), pas 8000 — 8000 n'est que le port interne au conteneur. Source de confusion récurrente en debug (`curl localhost:8000` échoue toujours de l'hôte).
- **Incident du 30/07/2026** : le conteneur `bourse_db` s'est retrouvé avec `NetworkSettings.Networks: {}` (aucun réseau attaché), alors que `bourse_backend` restait bien sur `bourse-app_default`. Le healthcheck Postgres passait quand même (il s'exécute en interne, via `localhost`), donc `docker compose ps` affichait `db` comme *healthy* alors que plus aucune requête backend→db n'aboutissait (`socket.gaierror: Name or service not known` sur le hostname `db`, coté asyncpg). Symptôme côté app : toutes les routes dépendant de la base échouaient en 500/empty reply — pas seulement `/assets`. Correctif : `docker compose down` (sans `-v`, le volume `bourse_pgdata` est conservé) puis `docker compose up -d`, qui réattache proprement les conteneurs au réseau. Cause probable : glitch réseau Docker Desktop/WSL2 après des redémarrages répétés — pas un bug applicatif. À surveiller si ça se reproduit.
- **`--reload` + bind mount** : `./backend:/app` est monté en volume et uvicorn tourne avec `--reload`, donc toute modification de fichier Python est prise en compte à chaud sans rebuild. Un `docker compose up -d --build backend` reste nécessaire uniquement en cas de changement de `requirements.txt` ou du `Dockerfile` — sinon il ne fait que recréer le conteneur inutilement (et ouvre une courte fenêtre où le port répond en TCP mais pas encore en HTTP, d'où d'éventuels `curl: (52) Empty reply from server` juste après le redémarrage).

## Dette technique et gaps connus

À traiter au fur et à mesure, pas tous en même temps (voir priorité #6 de `docs/risques-priorites-sources.md` : charge de maintenance solo).

1. **`users` orphelin** : login/register existent côté API mais aucune route n'est protégée (`portfolio`, `watchlist`, etc. sont globales, pas par utilisateur) et le frontend n'a ni store ni vue d'authentification. Rester en un seul utilisateur implicite tant que le besoin multi-utilisateur n'est pas confirmé (cf. priorité #10).
2. **`compliance_audit_log` orpheline** : table définie, jamais utilisée. Décider explicitement : soit l'implémenter (journalisation des textes de signal générés, utile si le produit s'ouvre à plusieurs utilisateurs, RGPD/FSMA), soit la retirer du schéma. Ne pas la laisser trainer indéfiniment.
3. **`docs/07-endpoints-fastapi.md`** annonçait 16 endpoints, il en existe 45 — document de conception à resynchroniser avec l'implémentation (ou à traiter explicitement comme historique/gelé, à trancher). L'écart s'est encore creusé depuis le 25/07 (36 → 38 → 43 → 44 → 45).
4. **README** annonçait 22 tests avant la mise à jour du 25/07/2026 (38 réels à l'époque, 56 aujourd'hui) — surveiller la dérive à chaque ajout de test.
5. **Alembic vs SQL brut** : maintenant que la révision `0001` existe, un déploiement Docker Compose existant (base déjà bootstrapée via `db/migrations/`) doit être *stampé* (`alembic stamp head`) avant d'appliquer une future migration Alembic, sinon Alembic tentera de recréer des tables déjà existantes. Pas encore fait automatiquement nulle part — à ajouter à la procédure de déploiement (`docs/16-plan-deploiement.md`) avant la prochaine évolution de schéma.
6. **Seed de données absent d'Alembic** (voir section Base de données) : contournement en place (`/seed-bel20`, `/seed-binance-majors`), mais aucune étape de démarrage ne les appelle automatiquement — à documenter clairement dans `docs/16-plan-deploiement.md` pour un futur déploiement propre, sinon même piège garanti sur une base fraîche.
7. **Paniers de seed figés en dur** (`assets/seed_data*.py` — BEL20, CAC40, DAX40, AEX, US majors, panier crypto) : contrairement à un indice officiel avec composition publiée en continu, ces listes sont des instantanés (voir dates de vérification en tête de chaque fichier) — à corriger manuellement si une composition change, ou à compléter à la demande via `POST /api/v1/assets` (déjà générique). Vérifier les tickers avant tout ajout futur : les places boursières renomment parfois un symbole (ex. `MATICUSDT` → `POLUSDT` sur Binance en septembre 2024, déjà pris en compte) sans avertissement dans l'app - un ticker obsolète ne casse rien (0 barre ingérée sur `/market-data/refresh-all`, pas d'erreur bloquante) mais reste silencieusement inutile jusqu'à correction.
8. **`training.build_training_set()` reste O(nb_signaux) en requetes DB** (une requete par signal pour ses explications, une autre pour son label futur) meme apres le correctif du 30/07/2026 (qui elimine seulement le facteur `x nb_actifs`, pas ce cout de base). Suffisant pour l'instant, mais a revisiter (requetes groupees/JOIN) si le nombre de signaux historiques devient tres grand (beaucoup d'actifs x beaucoup d'historique x 3 horizons).
9. **`/seed-everything` + `/market-data/refresh-all` = gros volume** (~189 actifs si tous les paniers sont seedés) : l'ingestion Yahoo Finance reste séquentielle (contrainte 429, voir docs/17), donc `refresh-all` peut prendre plusieurs minutes sur l'univers complet — pas de pagination ni de job en arrière-plan pour l'instant, l'appel HTTP reste bloquant jusqu'à la fin.

## Historique des mises à jour de ce document

- **30/07/2026 (suite 5)** — Bug reel trouvé en testant "Portefeuille virtuel" : `cash_balance` et `avg_cost` apparaissaient `null` dans `GET /api/v1/portfolio` alors que ces colonnes sont `NOT NULL`. Cause : Postgres autorise la valeur spéciale `NaN` pour un type `NUMERIC` (ce n'est pas un NULL), et Pydantic V2 sérialise `NaN` en JSON `null`. Origine du NaN : `yfinance` renvoie parfois une bougie du jour encore en formation avec des OHLC à `NaN` (marché pas encore clôturé, ou jour peu liquide) - `float(nan)` ne lève aucune exception, donc ce cours invalide entrait silencieusement dans `price_bars.close`, puis servait de base à un achat (`portfolio/service.py:buy()`), empoisonnant durablement `avg_cost` de la position ET `cash_balance` du portefeuille entier (NaN irréversible dans toute arithmétique ultérieure - `cash - NaN = NaN` pour toujours). Corrigé à trois niveaux : (1) `yahoo_finance.py` ignore désormais toute ligne dont un OHLC est NaN avant de la retourner ; (2) `market_data/repository.py:upsert_price_bars` filtre aussi en défense en profondeur (`_is_valid_bar`), au cas où un futur provider ne serait pas protégé ; (3) `portfolio/service.py:_get_latest_price` rejette explicitement un cours NaN ou ≤ 0 avant d'autoriser un achat/vente. 6 nouveaux tests (`tests/test_price_bar_validation.py`). **Ne corrige pas les données déjà corrompues** : un portefeuille dont `cash_balance` est déjà NaN reste NaN indéfiniment (aucune opération arithmétique ne peut le "réparer") - seul `POST /api/v1/portfolio/reset` permet de repartir sur une base saine. 62 tests au total (+6).
- **30/07/2026 (suite 4)** — Nouvelle page "Suivi des actifs" (`/status`, voir section Frontend) suite à une demande de voir le rafraîchissement progresser titre par titre plutôt qu'un bouton global opaque. Un seul endpoint ajouté côté backend (`GET /api/v1/assets/status`, agrégation en 4 requêtes) ; le rafraîchissement lui-même réutilise entièrement les endpoints par actif déjà existants, appelés en boucle côté client (`stores/assetStatus.js`) - choix délibéré pour éviter d'introduire une infra de jobs/streaming pour un besoin que les endpoints existants couvrent déjà. 45 endpoints (+1), build frontend vérifié (`npm run build`).
- **30/07/2026 (suite 3)** — Bug de performance réel trouvé en testant "Top achats" (`GET /api/v1/analyst/comparison-table`) après l'élargissement de l'univers d'actifs : l'endpoint semblait tourner indéfiniment. Cause : `signals_service.get_or_compute_signal()` reconstruisait entièrement le jeu d'entraînement ML (`training.build_training_set()` — un aller-retour DB par signal historique existant, tous actifs confondus) à **chaque actif** de la boucle, soit un `O(nb_actifs × nb_signaux)` — tolérable à 20-30 actifs, quasi infini à ~189. **Même défaut** trouvé dans `jobs/compute_signals_job.py` (le cron quotidien), touché de la même façon. Corrigé : `training_examples` peut désormais être précalculé une seule fois et réutilisé (nouveau paramètre optionnel sur `compute_signal_for_asset`, `get_or_compute_signal`, `_compute_ml_preview`, `get_comparison`) — `get_comparison_table` et `compute_signals_job` le construisent une fois en tête de fonction au lieu de le refaire à chaque itération. Aucun changement de comportement pour les appels unitaires (`GET /signals/{id}`, `POST /signals/{id}/recompute`) qui gardent l'ancien comportement par défaut. 56/56 tests toujours verts (pas de nouveau test ajouté ici : la correction ne change aucune sortie observable, seulement le nombre de requêtes DB - à couvrir un jour par un test de non-régression sur le nombre de requêtes si ce genre de régression doit être détecté automatiquement, voir gap ci-dessous).
- **30/07/2026 (suite 2)** — Ajout de `GET /api/v1/assets/discover-candidates` (voir section dédiée ci-dessus) suite à une demande de repérer des titres a suivre depuis l'actualité/les palmarès — recadré en liste de suggestions non automatique pour rester cohérent avec la philosophie "jamais de conseil" du projet. Premier essai avec des appels HTTP faits main vers les endpoints Yahoo non officiels (`/v1/finance/trending`, `/v7/finance/quote`) rejeté en 403 (protection anti-bot) ; réécrit pour réutiliser le screener intégré à `yfinance` (`yf.screen`), qui gère déjà cette authentification pour l'historique de prix. Non vérifié en conditions réelles (réseau sandbox restreint) — à tester après déploiement. 7 nouveaux tests, 44 endpoints (+1), 56 tests (+7).
- **30/07/2026 (suite)** — Élargissement de l'univers d'actifs, suite à une clarification : le panier crypto initial (8 valeurs) ne reflétait aucun avoir réel de l'utilisateur (aucune clé API Binance n'a jamais été utilisée — uniquement l'endpoint public `/klines`, voir plus bas), et l'utilisateur a demandé la couverture la plus large possible pour la simulation plutôt qu'un suivi de portefeuille réel. Ajouts : `seed_data_cac40.py` (39), `seed_data_dax.py` (39, Airbus exclu car déjà dans CAC40), `seed_data_aex.py` (25, ArcelorMittal exclu car doublon avec CAC40 potentiel), `seed_data_us.py` (34 megacaps NASDAQ/NYSE), panier crypto étendu de 8 à 32. Endpoints `/seed-cac40`, `/seed-dax40`, `/seed-aex`, `/seed-us-majors`, `/seed-everything`. Composition des indices vérifiée par recherche web (zonebourse.com pour le CAC40, Wikipedia/dax-indices.com pour le DAX40, Wikipedia/live.euronext.com pour l'AEX) plutôt que reconstituée de mémoire, y compris la correction d'un ticker potentiellement obsolète (Stellantis, STMicroelectronics). 5 nouveaux tests (`tests/test_seed_data.py`) qui garantissent l'absence de ticker dupliqué dans chaque liste et entre listes. Décompte : 43 endpoints (+5), 49 tests (+5), univers total ~189 actifs si tout est seedé.
- **30/07/2026** — Deux changements fonctionnels :
  - **Diagnostic « l'app ne trouve pas les actifs »** : cause réelle = conteneur `bourse_db` détaché du réseau Docker (`NetworkSettings.Networks: {}`), voir « Notes d'exploitation » ci-dessus — pas un problème de données. À l'occasion, un vrai gap a quand même été comblé : `alembic upgrade head` ne seedait jamais `assets` (voir section Base de données), corrigé par `assets/seed_data.py` + `POST /api/v1/maintenance/seed-bel20`, idempotent.
  - **Intégration Binance (lecture seule)** : nouveau `market_data/providers/binance.py` (API publique `/api/v3/klines`, sans clé, aucun ordre), sélection du provider par `Asset.market` (`market_data.service.provider_for_market()`), panier crypto de seed (`assets/seed_data_binance.py` + `/seed-binance-majors`), 6 nouveaux tests. Explicitement hors périmètre : passage d'ordres réels (Binance ou Admiral Markets) — écarté par choix, cohérent avec le portefeuille virtuel/simulé du domaine `portfolio` et la philosophie « jamais de conseil » du projet (voir `docs/17-limites-legales-techniques.md`). Admiral Markets n'a pas d'API REST retail de toute façon (MetaTrader 4/5 uniquement) — non traité.
  - Décompte resynchronisé : 12 domaines (11 annoncé par erreur le 25/07), 38 endpoints (+2), 44 tests (+6).
- **25/07/2026** — Création du document. Audit complet du dépôt (git status, tests, imports, schéma OpenAPI, cohérence Alembic/SQL). Corrections apportées : hygiène git (`.gitignore` supprimé par erreur restauré, fichiers `__pycache__`/`.env` désindexés), Alembic remis en état de marche (template manquant, imports de modèles incomplets, révision baseline générée et vérifiée), README resynchronisé (36 endpoints, 38 tests). Gaps documentés sans être corrigés : domaine `users` non câblé, table `compliance_audit_log` orpheline, doc `07-endpoints-fastapi.md` obsolète.
