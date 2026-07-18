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

# Frontend (autre terminal)
cd frontend
npm install
npm run dev
```

L'API est documentée automatiquement sur `http://localhost:8000/docs` (16 endpoints, voir `docs/07-endpoints-fastapi.md`). Le frontend tourne sur `http://localhost:5173`.

## État de la vérification

- Les 22 tests unitaires (`pytest backend/tests/ -v`) passent — moteur de score, NLP, indicateurs techniques, backtesting, garde-fous de conformité.
- L'application FastAPI complète s'importe et démarre sans erreur (schéma OpenAPI généré avec les 16 endpoints attendus, scheduler de jobs enregistré).
- Deux bugs réels ont été détectés et corrigés pendant cette vérification : une division par zéro dans le calcul du RSI pour une série de prix strictement croissante, et un calcul de confiance qui pouvait rester artificiellement élevé avec un historique de prix quasi inexistant. Les deux sont couverts par un test de non-régression.

## Rappel important

Ce livrable est une base de conception et un MVP de départ, pas un produit fini. Voir `docs/17-limites-legales-techniques.md` avant toute mise en production, en particulier sur le positionnement réglementaire (ce n'est ni un conseil en investissement, ni un service réglementé au sens FSMA en l'état) — à faire valider par un professionnel du droit financier si le projet dépasse un usage personnel.
