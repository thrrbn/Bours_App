"""
Endpoint de maintenance : declenche a la demande, en une seule requete, la
meme sequence que les jobs planifies (prix -> news -> signaux -> consensus
analystes), pour ne pas attendre les horaires cron (06h00/06h30/07h00) quand
on vient d'ajouter plusieurs actifs d'un coup (ex. seed BEL20).

Reutilise directement les fonctions de jobs/ - aucune logique dupliquee, et
le comportement planifie reste strictement identique.
"""
from fastapi import APIRouter

from app.jobs.compute_signals_job import compute_signals_job
from app.jobs.ingest_news_job import ingest_news_job
from app.jobs.ingest_prices_job import ingest_prices_job
from app.jobs.refresh_analyst_ratings_job import refresh_analyst_ratings_job

router = APIRouter(prefix="/api/v1/maintenance", tags=["maintenance"])


@router.post("/refresh-all")
async def refresh_all():
    """
    Sequentiel et volontairement lent (pas de parallelisation) : Yahoo Finance
    bloque les rafales de requetes (429), voir docs/17. Prevoir 30s-1min pour
    20 actifs.
    """
    prices = await ingest_prices_job()
    news = await ingest_news_job()
    signals = await compute_signals_job()
    analyst = await refresh_analyst_ratings_job()

    return {
        "prices": prices,
        "news": news,
        "signals": signals,
        "analyst": analyst,
    }
