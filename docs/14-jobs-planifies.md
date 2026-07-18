# 14. Jobs planifiés

## Pourquoi APScheduler et pas Celery en V1

Celery apporte de la valeur quand (a) les tâches doivent être distribuées sur plusieurs machines/workers, (b) le volume de tâches dépasse la capacité d'un scheduler in-process, ou (c) on a besoin de files de priorité et de retry sophistiqué avec persistance externe (Redis/RabbitMQ). En V1, avec quelques jobs quotidiens sur une dizaine à quelques centaines d'actifs, aucune de ces conditions n'est vraie. Ajouter Celery + Redis maintenant, c'est ajouter deux composants d'infrastructure supplémentaires (déploiement, monitoring, mode de panne) sans bénéfice mesurable — exactement le type de complexité que ce projet doit éviter pour un solo développeur (voir doc 03).

`APScheduler` (`AsyncIOScheduler`) tourne **dans le même process** que FastAPI, démarré via le hook `lifespan` de l'application. C'est suffisant, simple à déboguer (les logs sont dans le même flux que l'API), et suffisant à réévaluer seulement si la mesure réelle (durée d'exécution, volume d'actifs suivis) montre une limite atteinte.

## Jobs définis en V1

| Job | Fréquence | Rôle |
|---|---|---|
| `ingest_prices_job` | Quotidien, 06:00 (après clôture des marchés US, avant ouverture Europe) | Ingestion des derniers prix/volumes manquants + recalcul des indicateurs techniques |
| `ingest_news_job` | Toutes les 2h en journée (06:00-20:00) | Ingestion des nouveaux articles RSS, scoring sentiment + mots-clés |
| `compute_signals_job` | Quotidien, 07:00 (après les deux jobs précédents) | Recalcul des signaux (3 horizons) pour tous les actifs actifs |
| `cleanup_stale_watchlist_job` (V2) | Hebdomadaire | Nettoyage des actifs inactifs non suivis depuis longtemps |

## Séquencement et dépendances
`compute_signals_job` ne doit démarrer qu'après la fin de `ingest_prices_job` et d'au moins une exécution récente de `ingest_news_job`. En V1, ceci est géré simplement par des horaires décalés (06:00 / toutes les 2h / 07:00) avec une marge suffisante. Si la fiabilité de ce séquencement devient un problème réel (jobs qui débordent de leur fenêtre), la solution est d'enchaîner explicitement les jobs en callback plutôt que de complexifier avec un orchestrateur dédié (Airflow serait disproportionné pour ce volume).

## Gestion des erreurs
- Chaque job est encapsulé dans un `try/except` par actif : une erreur sur un ticker est loggée et n'interrompt pas le traitement des autres.
- Un résumé d'exécution (nombre d'actifs traités, nombre d'erreurs, durée) est loggé à la fin de chaque job et consultable via les logs applicatifs (V2 : exposition d'un endpoint `/api/v1/jobs/last-run` pour un monitoring simple sans outil externe).

## Exemple d'enregistrement (`backend/app/jobs/scheduler.py`)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

def register_jobs():
    scheduler.add_job(ingest_prices_job, CronTrigger(hour=6, minute=0), id="ingest_prices", replace_existing=True)
    scheduler.add_job(ingest_news_job, CronTrigger(minute=0, hour="6-20/2"), id="ingest_news", replace_existing=True)
    scheduler.add_job(compute_signals_job, CronTrigger(hour=7, minute=0), id="compute_signals", replace_existing=True)
```

## Ré-évaluation vers Celery (critère objectif, pas une intuition)
Passer à Celery + Redis seulement si l'une de ces conditions est mesurée : (1) le nombre d'actifs suivis dépasse plusieurs milliers et le job d'ingestion ne tient plus dans sa fenêtre horaire, (2) plusieurs utilisateurs déclenchent des recalculs à la demande simultanément et saturent le process API, ou (3) un besoin de traitement distribué sur plusieurs machines apparaît réellement (ex. calcul NLP lourd nécessitant un GPU dédié). Tant que ces critères ne sont pas atteints, ajouter Celery serait de la complexité anticipée non justifiée.
