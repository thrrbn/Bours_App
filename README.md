# Bourse Assistant — livrable de conception

Assistant d'analyse boursière pour investisseurs particuliers en Belgique : scores explicables, jamais de conseil en investissement. Voir `docs/01-vision-produit.md` pour le détail.

## Comment naviguer ce livrable

- **`docs/`** — les 17 livrables demandés (vision, architecture, schéma de base de données, stratégies NLP/prévision/scoring, endpoints, pipeline, déploiement, limites légales, risques/priorités/sources), un fichier par thème, numérotés dans l'ordre du cahier des charges.
- **`LEARNING_PATH.md`** — parcours pédagogique par modules progressifs pour reconstruire le projet vous-même, dans le même esprit que votre formation GMAO.
- **`backend/`** — code Python exécutable (FastAPI, SQLAlchemy, moteur de score, NLP, jobs planifiés). Couvert par des tests unitaires (`backend/tests/`), tous vérifiés fonctionnels.
- **`frontend/`** — squelette Vue 3 + Vite + Pinia + Tailwind (recherche d'actif, dashboard de signal, historique).

## Démarrage rapide (MVP local)

```bash
# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ajuster DATABASE_URL et JWT_SECRET_KEY
alembic upgrade head    # une fois les migrations générées (alembic revision --autogenerate)
uvicorn app.main:app --reload
curl -X POST http://localhost:8000/api/v1/maintenance/seed-bel20            # peuple les 20 actifs BEL20 (schema seul via alembic, sans données)
curl -X POST http://localhost:8000/api/v1/maintenance/seed-everything       # optionnel : + CAC40, DAX40, AEX, megacaps US, panier crypto Binance (~190 actifs)

# Frontend (autre terminal)
cd frontend
npm install
npm run dev
```

L'API est documentée automatiquement sur `http://localhost:8000/docs` (36 endpoints au 25/07/2026, voir `docs/07-endpoints-fastapi.md` et `docs/STACK.md` pour le décompte à jour). Le frontend tourne sur `http://localhost:5173`.

⚠️ `alembic upgrade head` crée uniquement le schéma, jamais de données : sans l'appel à `/api/v1/maintenance/seed-bel20` ci-dessus, la table `assets` reste vide et l'application ne trouve aucun actif (`/api/v1/assets` renvoie `[]`). C'est le seul chemin de seed sur une base initialisée via Alembic — `db/migrations/004_bel20_seed.sql` ne joue automatiquement que sur un volume Postgres neuf (`docker-entrypoint-initdb.d`).

## État de la vérification

- Les 38 tests unitaires (`pytest backend/tests/ -v`) passent — moteur de score, NLP, indicateurs techniques, backtesting, garde-fous de conformité.
- L'application FastAPI complète s'importe et démarre sans erreur (schéma OpenAPI généré avec les 36 endpoints attendus, scheduler de jobs enregistré).
- Deux bugs réels ont été détectés et corrigés pendant la vérification initiale : une division par zéro dans le calcul du RSI pour une série de prix strictement croissante, et un calcul de confiance qui pouvait rester artificiellement élevé avec un historique de prix quasi inexistant. Les deux sont couverts par un test de non-régression.
- 25/07/2026 : `backend/alembic/` ne fonctionnait pas (template `script.py.mako` absent, et `env.py` n'important que 6 des 11 domaines vers `target_metadata`, donc `alembic revision --autogenerate` aurait silencieusement omis `analyst`, `notifications`, `portfolio` et `watchlist`). Corrigé et vérifié : `alembic upgrade head`/`downgrade base` testés sur un Postgres jetable, schéma identique aux 16 tables métier de `db/migrations/001-007` (voir `docs/STACK.md`, section « Base de données »).

Voir `docs/STACK.md` pour l'état détaillé de la stack, mis à jour à chaque session de développement.

## Rappel important

Ce livrable est une base de conception et un MVP de départ, pas un produit fini. Voir `docs/17-limites-legales-techniques.md` avant toute mise en production, en particulier sur le positionnement réglementaire (ce n'est ni un conseil en investissement, ni un service réglementé au sens FSMA en l'état) — à faire valider par un professionnel du droit financier si le projet dépasse un usage personnel.

…or create a new repository on the command line

echo "# bourse_app" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/thrrbn/bourse_app.git
git push -u origin main


…or push an existing repository from the command line

git remote add origin https://github.com/thrrbn/bourse_app.git
git branch -M main
git push -u origin main
# bourse_app
# Bours_App
# Bours_App
# Bours_App
