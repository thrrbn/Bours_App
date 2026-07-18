# Parcours pédagogique — Bourse Assistant

Ce parcours découpe le projet en modules progressifs, du plus simple au plus complexe, dans le même esprit que votre formation GMAO : chaque module explique un concept, vous laisse l'écrire vous-même, puis propose un exercice de vérification concret. Le code déjà présent dans `backend/` et `frontend/` sert de **corrigé de référence** — l'idée n'est pas de le recopier, mais de reconstruire chaque brique à votre rythme en vous y référant quand vous êtes bloqué ou pour comparer votre solution.

Chaque module indique : l'objectif, le concept Python/architecture qui est appris, ce qu'il faut coder, le fichier de référence correspondant, et un exercice de vérification qui prouve que ça fonctionne.

## Module 0 — Environnement de travail

**Objectif** : avoir un environnement Python reproductible, avant d'écrire une seule ligne de logique métier.

**Concept appris** : environnements virtuels, gestion des dépendances, variables d'environnement (`.env`), différence entre configuration et code.

**À faire** :
1. Créer un environnement virtuel (`python3.12 -m venv .venv`), l'activer.
2. Installer les dépendances de `backend/requirements.txt`.
3. Copier `.env.example` vers `.env`, comprendre chaque variable.
4. Lancer PostgreSQL en local (Docker : `docker run -e POSTGRES_PASSWORD=... postgres:16`).

**Fichier de référence** : `backend/requirements.txt`, `backend/.env.example`, `backend/app/config.py`.

**Exercice de vérification** : `python -c "from app.config import get_settings; print(get_settings())"` doit afficher vos settings sans erreur.

## Module 1 — Le domaine `assets` : votre premier CRUD

**Objectif** : comprendre le découpage en couches (models/schemas/repository/service/router) sur le domaine le plus simple du projet.

**Concept appris** : ORM déclaratif (SQLAlchemy), séparation modèle de données (base) / contrat API (Pydantic), pourquoi le router ne doit jamais contenir de logique métier.

**À faire** :
1. Écrire `models.py` (table `Asset`) sans regarder la référence, à partir du schéma SQL (`docs/05-schema-postgresql.sql`).
2. Écrire `schemas.py` (`AssetCreate`, `AssetRead`).
3. Écrire `repository.py` (fonctions `get_by_id`, `search`, `create`) — uniquement des requêtes, pas de règles.
4. Écrire `service.py` puis `router.py`.

**Fichier de référence** : `backend/app/domains/assets/`.

**Exercice de vérification** : démarrer l'API (`uvicorn app.main:app --reload`), créer un actif via `POST /api/v1/assets`, le retrouver via `GET /api/v1/assets/search?q=...`.

## Module 2 — Ingestion de prix et indicateurs techniques

**Objectif** : comprendre le pattern "provider abstrait" et manipuler pandas pour du calcul financier.

**Concept appris** : interfaces abstraites (`ABC`) pour isoler une dépendance externe fragile (Yahoo Finance), calcul vectorisé avec pandas (`rolling`, `ewm`), gestion des cas limites (division par zéro dans le RSI — un vrai bug rencontré et corrigé pendant la construction de ce projet, voir `app/domains/market_data/service.py::_rsi`).

**À faire** :
1. Écrire l'interface `MarketDataProvider` (`providers/base.py`).
2. Implémenter `YahooFinanceProvider` avec `yfinance`.
3. Écrire `compute_indicators_dataframe()` : SMA, EMA, RSI, MACD, Bollinger, volatilité — une fonction à la fois, en la testant isolément avant de passer à la suivante.

**Fichier de référence** : `backend/app/domains/market_data/`.

**Exercice de vérification** : `backend/tests/test_market_data_indicators.py` doit passer (`pytest tests/test_market_data_indicators.py -v`). Portez une attention particulière au cas d'une série de prix strictement croissante (RSI proche de 100) — c'est le cas qui a révélé un bug de division par zéro pendant le développement de ce projet.

## Module 3 — NLP et scoring de sentiment

**Objectif** : construire un moteur de sentiment simple, explicable, sans machine learning.

**Concept appris** : approche lexicon-based (dictionnaire pondéré), normalisation de texte (accents, casse), pourquoi la simplicité prime sur la sophistication en V1 (voir `docs/09-strategie-nlp-sentiment.md`).

**À faire** :
1. Construire `lexicon.py` avec vos propres poids pour les mots-clés du cahier des charges.
2. Écrire `score_sentiment()` : neutre par défaut, borné entre -1 et 1.
3. Écrire `extract_keywords()` : retrouver les mots-clés et leur horizon d'impact.

**Fichier de référence** : `backend/app/domains/news/nlp/`.

**Exercice de vérification** : `pytest tests/test_news_sentiment.py -v`. Essayez d'ajouter un mot-clé de votre choix au lexique et vérifiez que le test correspondant capte bien le changement.

## Module 4 — Le moteur de score (le cœur du produit)

**Objectif** : construire le moteur de règles pondérées qui transforme des features en signal explicable.

**Concept appris** : dataclasses pour structurer un résultat complexe, séparation stricte entre calcul du score et génération de l'explication textuelle, garantie que chaque composante porte toujours un texte non vide.

**À faire** :
1. Écrire `SignalFeatures` (dataclass) dans `features.py`.
2. Écrire une à une les fonctions `compute_technical_score`, `compute_news_score`, `compute_risk_score`, `compute_confidence_score`.
3. Écrire `_final_signal()` : la logique de décision (achat spéculatif / surveillance / neutre / prudence / vente défensive).
4. Assembler le tout dans `compute()`.

**Fichier de référence** : `backend/app/domains/signals/models_ml/baseline_rules.py`.

**Exercice de vérification** : `pytest tests/test_signals_engine.py -v`. Ce module a lui aussi révélé un bug réel pendant le développement : un historique de prix très court combiné à des actualités fraîches donnait une confiance artificiellement élevée. Le test `test_low_confidence_forces_surveillance_regardless_of_scores` vérifie que ce cas est bien couvert — essayez de comprendre pourquoi le calcul de `data_completeness` a un plancher à 20 jours avant de regarder la solution.

## Module 5 — Gouvernance : les garde-fous de formulation

**Objectif** : comprendre pourquoi un produit financier a besoin de garde-fous automatisés, pas seulement de bonnes intentions.

**Concept appris** : validation post-génération de texte, centralisation des textes légaux (une seule source de vérité).

**À faire** : écrire `validate_signal_wording()` qui lève une erreur si un terme interdit apparaît dans un texte généré.

**Fichier de référence** : `backend/app/domains/compliance/`.

**Exercice de vérification** : `pytest tests/test_compliance_guardrails.py -v`.

## Module 6 — Orchestration et jobs planifiés

**Objectif** : faire tourner le pipeline complet (ingestion → NLP → scoring) automatiquement, sans dupliquer de logique entre l'API et les jobs.

**Concept appris** : APScheduler, pourquoi les jobs réutilisent les mêmes fonctions `service.py` que les endpoints API, gestion d'erreur par actif (un échec isolé ne bloque pas le reste).

**À faire** : écrire `ingest_prices_job`, `ingest_news_job`, `compute_signals_job`, puis les enregistrer dans `scheduler.py`.

**Fichier de référence** : `backend/app/jobs/`.

**Exercice de vérification** : démarrer l'API et vérifier dans les logs que les 3 jobs sont bien enregistrés au démarrage ("Jobs planifiés enregistrés...").

## Module 7 — Assembler l'API complète

**Objectif** : monter tous les routers dans `main.py` et obtenir une API testable de bout en bout.

**Concept appris** : `lifespan` FastAPI, CORS, gestion d'exceptions centralisée.

**Exercice de vérification** :
```
uvicorn app.main:app --reload
curl http://localhost:8000/api/v1/health
```
puis ouvrir `http://localhost:8000/docs` (Swagger UI généré automatiquement) et vérifier que les 16 endpoints du produit (voir `docs/07-endpoints-fastapi.md`) apparaissent tous.

## Module 8 — Backtesting

**Objectif** : mesurer objectivement si le moteur de score "a raison" historiquement.

**Concept appris** : validation walk-forward (pas de fuite de données futures), métriques de précision/drawdown.

**À faire** : écrire `evaluate_signals()` à partir d'une liste de résultats (signal, rendement réel constaté). Puis, en exercice plus avancé, compléter l'orchestration dans `backtests/router.py::run_backtest` pour qu'elle récupère réellement l'historique des signaux et les prix futurs depuis la base (actuellement un point d'extension marqué dans le code).

**Fichier de référence** : `backend/app/domains/backtests/service.py`.

**Exercice de vérification** : `pytest tests/test_backtests_metrics.py -v`.

## Module 9 — Frontend : consommer l'API

**Objectif** : afficher un signal complet avec ses explications dans une interface simple.

**Concept appris** : Pinia (state management), composition API Vue 3, jamais de logique métier dans un composant (tout passe par un store qui appelle l'API).

**À faire** : construire `useAssetsStore`, `useSignalsStore`, puis les vues `AssetSearchView` et `DashboardView`.

**Fichier de référence** : `frontend/src/`.

**Exercice de vérification** : `npm install && npm run dev`, rechercher un actif préalablement créé via l'API, vérifier que le signal s'affiche avec ses explications et le disclaimer.

## Module 10 — Déploiement local complet

**Objectif** : faire tourner l'ensemble (PostgreSQL + API + frontend) en local via Docker Compose, première étape avant la mise en production (`docs/16-plan-deploiement.md`).

**Exercice de vérification** : depuis zéro (base vide), exécuter `alembic upgrade head`, créer un actif, attendre (ou déclencher manuellement) les jobs d'ingestion, vérifier qu'un signal explicable apparaît dans le frontend.

## Comment utiliser ce parcours

Vous n'êtes pas obligé de suivre l'ordre à la lettre, mais chaque module suivant s'appuie sur les précédents (le moteur de score a besoin des indicateurs techniques et du sentiment ; le frontend a besoin de l'API complète). Le rythme naturel : un module = une session de travail. Si un exercice de vérification échoue, comparez votre code avec le fichier de référence ligne par ligne plutôt que de le copier directement — c'est cette comparaison qui construit la compréhension, pas la copie.
