# 16. Plan de déploiement

## Étape 0 — MVP local (développement)
- `docker-compose.yml` avec deux services : `postgres` (image officielle, volume persistant local) et `api` (build du backend FastAPI, hot-reload en dev via `uvicorn --reload`).
- Frontend Vue lancé séparément en dev (`npm run dev`, proxy Vite vers l'API locale).
- Fichier `.env` local (jamais commité — `.env.example` versionné à la place).
- Migrations Alembic appliquées manuellement (`alembic upgrade head`) au démarrage du conteneur `api` (script d'entrypoint).

## Étape 1 — Environnement de test / staging
- Même `docker-compose`, déployé sur une petite VM (ex. Hetzner, OVH, Scaleway — hébergeurs européens à coût maîtrisé, pertinent pour un usage belge/UE et la question de résidence des données, voir doc 17).
- Base PostgreSQL avec sauvegarde automatique quotidienne (`pg_dump` planifié + rétention 7 jours minimum).
- Jeu de données réduit (10-20 actifs) pour valider le pipeline complet en conditions réelles avant d'ouvrir plus largement.

## Étape 2 — Production V1
- Reverse proxy (Caddy ou Nginx) devant l'API FastAPI : gestion TLS (Let's Encrypt automatique avec Caddy — le plus simple pour un solo dev), compression, en-têtes de sécurité.
- Frontend Vue buildé statiquement (`npm run build`) et servi soit par le même reverse proxy, soit via un hébergement statique séparé (Netlify/Vercel/Cloudflare Pages) qui appelle l'API sur son domaine dédié (`api.bourse-assistant.be` par exemple).
- Variables sensibles (secret JWT, éventuelle clé Benzinga) gérées via des secrets d'environnement du serveur, jamais en dur dans l'image Docker.
- Processus API supervisé (systemd ou le restart policy Docker `unless-stopped`), logs redirigés vers un fichier rotatif ou un service de logs géré simple (ex. Better Stack / Papertrail, plans gratuits suffisants au volume visé).

## Schéma de déploiement V1

```
Internet
   │
   ▼
Reverse proxy (Caddy, TLS auto)
   │
   ├── / (statique)        → build Vue.js
   └── /api/*              → conteneur FastAPI (uvicorn/gunicorn)
                                   │
                                   ▼
                            PostgreSQL (conteneur ou managé)
                                   │
                            Jobs APScheduler (in-process, même conteneur API)
```

## Sauvegarde et continuité
- Sauvegarde quotidienne de la base (pg_dump vers stockage objet, ex. Backblaze B2/OVH Object Storage — coût minime).
- Les modèles/config de scoring sont versionnés dans le repo Git (pas seulement en base), donc reconstructibles indépendamment de la base de données.

## CI/CD minimal, adapté à un solo dev
- GitHub Actions (ou GitLab CI) : sur chaque push sur `main`, exécution des tests (`pytest`), puis build de l'image Docker, puis déploiement (SSH + `docker compose pull && up -d`, ou un service de déploiement simple type Coolify/Dokku qui évite de gérer soi-même Kubernetes — disproportionné pour ce périmètre).
- Pas de blue/green deployment ni de canary release en V1 : la fenêtre d'indisponibilité de quelques secondes lors d'un redéploiement est acceptable pour un outil d'aide à la décision consulté de façon asynchrone (pas un système temps réel critique).

## Migration future (mise à l'échelle si le produit prend de l'ampleur)
Si le produit dépasse le cadre solo (plus d'utilisateurs, besoin de calcul NLP plus lourd) : possibilité d'extraire le domaine `news`/NLP en service séparé avec sa propre capacité de calcul (GPU), en gardant l'API principale comme monolithe pour tout le reste — la séparation en domaines internes (doc 03) rend cette extraction chirurgicale plutôt qu'une réécriture.
