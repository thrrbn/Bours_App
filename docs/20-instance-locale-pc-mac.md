# Instance locale PC/Mac : analyste IA integre a l'application

## Pourquoi ce document existe

`docs/19-outils-pc-autonomes.md` pose un principe : tout besoin de calcul lourd (LLM local, futures donnees alternatives) vit dans `tools/`, en dehors de `backend/`/`frontend/`, jamais couple a l'application deployee. `tools/backtest_analyst/` (14/08/2026) suit ce principe a la lettre.

Le 16/08/2026, demande explicite : integrer cette meme analyse **dans l'application elle-meme** (une vraie page, pas un script en ligne de commande), a condition que ça reste strictement reserve a une instance tournant en local sur un PC/Mac - jamais sur le NAS deploye. C'est une exception deliberee au principe de `docs/19`, pas un remplacement : les deux approches coexistent (voir "Coexistence avec `tools/backtest_analyst/`" plus bas).

## Ce qui a ete construit

Un domaine backend `backend/app/domains/llm_analyst/` (schemas, service, router, job asynchrone) qui **vit dans le meme code que celui deploye sur le NAS**, mais reste desactive par defaut :

- `Settings.enable_llm_analyst` (voir `backend/app/config.py`) vaut `False` par defaut. Le `docker-compose.yml` deploye sur le NAS ne definit jamais cette variable - la feature y reste donc toujours desactivee, meme si le code est present dans le meme depot Git.
- `router.py::require_enabled()` bloque `POST /api/v1/llm-analyst/analyze` avec une erreur 403 explicite tant que ce flag n'est pas `true`. Defense en profondeur : meme si quelqu'un active le flag par erreur sur une machine sans Ollama, le pire cas est une erreur claire ("Ollama injoignable"), jamais un calcul silencieusement degrade.
- Le frontend n'affiche le lien de navigation "Analyste IA" que si `GET /api/v1/llm-analyst/status` renvoie `enabled: true` - decide a l'**execution**, pas a la compilation. Le meme build du frontend fonctionne donc correctement pointe vers le NAS (lien absent) ou vers une instance locale (lien present), sans avoir a maintenir deux builds distincts.

## Pourquoi c'est quand meme sans risque pour le NAS

Trois raisons independantes, pas juste une convention :

1. **Flag desactive par defaut** - il faut une action explicite (ajouter `ENABLE_LLM_ANALYST=true` a un `.env` local) pour l'activer, jamais le cas par defaut.
2. **Le NAS n'a pas Ollama** - meme flag active par erreur, `OllamaProvider._call_model()` echouerait immediatement avec une erreur de connexion claire (voir `llm_provider.py`), jamais une reponse degradee ou un calcul qui tourne quand meme.
3. **Le job tourne hors du cycle de requete** - comme `deep_training_job.py` (LSTM, Phase 3), l'appel au LLM est asynchrone (`scheduler.add_job` + polling) : meme dans le pire cas, un appel bloque ne fige jamais une requete HTTP normale plus de quelques millisecondes.

## Difference avec `tools/backtest_analyst/` : cours ajuste

`kernc_engine.py::_load_price_dataframe` (deja utilise par le moteur de backtest principal) retraite Open/High/Low/Close par le facteur d'ajustement dividendes/splits (`adjusted_close`). L'API publique en lecture seule qu'utilise `tools/backtest_analyst/` (via `tools/shared/nas_api_client.py`) n'expose PAS cette colonne - elle travaille donc sur le cours brut. Consequence : une analyse lancee depuis cette page integree peut legerement differer (quelques % de rendement sur plusieurs annees, sur un titre a dividendes reguliers) de celle produite par le CLI de `tools/backtest_analyst/` sur le meme ticker/periode. Ce n'est pas un bug, c'est la meme divergence deja documentee dans `tools/backtest_analyst/README.md`, juste inversee (c'est ici la version integree qui est la plus precise des deux, cette fois).

Nuance : si les prix ont ete peuples via `import_from_nas.py` (voir plus bas) plutot que via `ingest_prices_job` (Yahoo Finance), `adjusted_close` reste `None` meme dans la base locale - meme limitation que `tools/backtest_analyst/` pour CES actifs precis, tant qu'un rafraichissement Yahoo Finance ne les remplace pas.

## Duplication de code assumee (et son cout)

`backend/app/domains/llm_analyst/quant_facts.py`, `llm_provider.py` et `analyst.py` sont des copies quasi-identiques de `tools/backtest_analyst/{quant_facts,llm_provider,analyst}.py`, pas des imports - meme raisonnement que `tools/backtest_analyst/strategies.py` (deja duplique dans l'autre sens) : `backend/app` n'importe jamais `tools/`, et reciproquement (voir `docs/19`, point 5 du contrat).

**Cout reel de ce choix** : toute future correction d'un probleme de qualite du LLM (nouveau bug reel observe, sur le modele des trois deja corriges dans `tools/backtest_analyst/analyst.py` le 14-16/08/2026) doit etre appliquee **dans les deux copies**. Rien ne les synchronise automatiquement. Point de vigilance a surveiller : si cette divergence devient penible en pratique (plus de 2-3 corrections desynchronisees), il vaudra la peine d'extraire la logique commune dans un troisieme emplacement partage - mais pas par anticipation tant que ce n'est pas encore arrive (meme discipline que le "point de vigilance" de `docs/19`).

## Coexistence avec `tools/backtest_analyst/`

Les deux approches restent valides, pour des besoins differents :

- **`tools/backtest_analyst/` (CLI)** : le plus leger des deux - un seul script Python, aucune base de donnees locale a maintenir, interroge le NAS a chaque appel. Ideal pour une analyse ponctuelle sans vouloir faire tourner toute l'application en local.
- **Cette page integree** : plus confortable (formulaire, historique visible dans l'app), mais demande de faire tourner backend + frontend + une base Postgres locale, et de peupler cette base au prealable (voir ci-dessous). Cours ajuste des dividendes, contrairement au CLI.

## Installation (instance locale)

Prerequis : avoir deja le depot clone, et suivre le "Demarrage rapide (MVP local)" du `README.md` principal (backend via `uvicorn`, frontend via `npm run dev`) - PAS le `docker-compose.yml` de deploiement NAS complet (qui n'expose pas ces variables).

1. **Base de donnees locale.** Le plus simple : ne lancer QUE le service `db` du `docker-compose.yml` existant (`docker compose up -d db`, deja configure sur le port hote `5433`) plutot que d'installer un Postgres a part - ou utiliser un Postgres deja installe localement.
2. **Ollama** : installer [Ollama](https://ollama.com), puis `ollama pull llama3.1` (ou un modele plus leger si peu de RAM, voir `tools/backtest_analyst/README.md` pour les memes recommandations).
3. **`backend/.env`** : ajouter (voir `.env.example`) :
   ```
   DB_HOST=localhost
   DB_PORT=5433
   ENABLE_LLM_ANALYST=true
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.1
   ```
4. **Migrations** : `alembic upgrade head` (cree `llm_analysis_jobs`, voir `alembic/versions/0014_llm_analysis_jobs.py`).
5. **Peupler les actifs suivis** : soit `curl -X POST http://localhost:8000/api/v1/maintenance/seed-bel20` (ou `seed-everything`) puis laisser `ingest_prices_job` tourner (cron quotidien, cours ajustes via Yahoo Finance) - soit, plus rapide pour un premier essai, importer directement les donnees deja suivies sur le NAS :
   ```
   python -m app.jobs.import_from_nas --nas-url http://192.168.88.10:8082
   ```
   Voir `backend/app/jobs/import_from_nas.py` pour le detail (lecture seule vers le NAS, jamais l'inverse - meme sens que `tools/shared/nas_api_client.py`).
6. Lancer `uvicorn app.main:app --reload` (backend) et `npm run dev` (frontend) comme d'habitude. Le lien "Analyste IA" apparait dans la navigation.

## Ce qui n'est volontairement pas fait dans cette premiere version

- Pas de `docker-compose.local.yml` dedie : la base `db` du compose existant suffit, pas besoin de dupliquer toute la stack Docker pour ce cas d'usage.
- Pas de synchronisation automatique/recurrente NAS -> local : `import_from_nas.py` est un script manuel, a relancer a la demande (pas un cron, voir sa docstring).
- Pas de `signal_replay` (memes raisons que `tools/backtest_analyst/`, voir `kernc_engine.py::LLM_ANALYST_SUPPORTED_STRATEGIES`).
- Pas de laboratoire de parametres pour cette page (toujours les reglages par defaut de chaque strategie) - coherent avec le perimetre deja pose dans `tools/backtest_analyst/`.
