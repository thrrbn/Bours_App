# Outils autonomes PC/Mac (tools/)

## Principe

Certains besoins (analyse assistée par LLM, futures pistes de données alternatives évoquées le 14/08/2026 - SEC EDGAR, Wikipedia Pageviews, GDELT) demandent un calcul trop lourd pour le NAS qui héberge l'application. Plutôt que de forcer ce calcul sur une machine qui n'est pas dimensionnée pour, ces outils vivent dans `tools/`, à part de `backend/` et `frontend/`, et tournent **uniquement sur le PC ou le Mac de l'utilisateur**.

Ce n'est pas une préférence de confort : c'est une contrainte matérielle confirmée. Le NAS Asustor sur lequel l'application est déployée n'a pas de GPU, et le projet applique déjà cette discipline ailleurs - voir `docs/09-strategie-nlp-sentiment.md`, qui cantonne explicitement FinBERT (le seul autre modèle un peu lourd envisagé) à un job batch, jamais synchrone sur une requête HTTP, "selon les ressources CPU disponibles". `tools/` généralise ce principe déjà établi à son aboutissement logique : quand même le mode batch reste trop lourd pour le NAS, l'outil ne tourne pas sur le NAS du tout.

## Le contrat

Tout outil ajouté sous `tools/` doit respecter ceci :

1. **Lecture seule vers le NAS, jamais l'inverse.** L'outil interroge l'API publique déjà existante du backend (voir `tools/shared/nas_api_client.py`) - jamais d'accès direct à la base Postgres, jamais d'écriture. Le NAS n'appelle jamais le PC : cette direction serait fragile (dépend que la machine soit allumée et joignable), l'outil doit toujours être celui qui initie la connexion.
2. **Code partagé factorisé dans `tools/shared/`.** Le client API en lecture seule (`nas_api_client.py`) y vit déjà - tout nouvel outil qui a besoin de lire des prix ou des tickers suivis l'importe depuis là plutôt que de le recopier (voir `tools/shared/README.md` pour le mécanisme d'import).
3. **README explicite dès la première ligne.** Chaque outil documente immédiatement qu'il doit tourner sur un PC/Mac, jamais sur le NAS, et pourquoi (voir `tools/backtest_analyst/README.md` comme référence).
4. **Environnement virtuel dédié**, jamais d'installation dans l'environnement Python global de l'utilisateur (voir la section installation de `tools/backtest_analyst/README.md`).
5. **Jamais couplé à la configuration du backend.** Ne pas importer directement du code sous `backend/app/` si ça entraîne toute l'arborescence `app.*` (settings Pydantic, connexion DB...) à sa suite - dupliquer volontairement le strict nécessaire (voir `tools/backtest_analyst/strategies.py`, qui documente ce compromis) plutôt que de dépendre d'une configuration qui n'a pas de raison d'exister sur un PC.

## Référence

`tools/backtest_analyst/` (14/08/2026) : analyste de backtest assisté par un LLM local (Ollama). Premier outil de ce type, sert d'exemple pour tout ce qui suivrait le même schéma - voir son `README.md` pour le détail de fonctionnement.

## Ce qui n'est pas encore fait, pour mémoire

Deux pistes évoquées le 14/08/2026 suivraient le même principe si elles sont un jour construites :

- Un générateur de features techniques par LLM (boucle de recherche : proposition de formules, calcul de l'Information Coefficient sur le train uniquement, holdout jamais touché) - mis de côté en dernier dans l'ordre convenu, à cause du risque de p-hacking si les garde-fous statistiques (correction pour tests multiples, deflated Sharpe ratio) ne sont pas solides.
- Ingestion de données alternatives gratuites (SEC EDGAR pour les tickers US, Wikipedia Pageviews comme proxy d'attention retail, GDELT en réserve) - toutes lisibles/traitables depuis un PC, jamais depuis le NAS.

## Point de vigilance

Un seul outil existe aujourd'hui. Si 2-3 outils de plus s'accumulent sous `tools/`, il vaudra la peine de revisiter s'il faut factoriser davantage (au-delà du client API déjà partagé) - pas la peine de le faire par anticipation tant que ce n'est pas encore arrivé.
