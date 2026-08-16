"""
Job asynchrone de l'analyste IA (16/08/2026, voir docs/20-instance-locale-pc-mac.md)
- meme pattern que jobs/deep_training_job.py (Phase 3) : un appel a un
modele local (ici Ollama, jusqu'a plusieurs minutes) prend trop longtemps
pour un appel HTTP synchrone.

Declenche a la demande (POST /api/v1/llm-analyst/analyze, voir
domains/llm_analyst/router.py) via `scheduler.add_job(..., trigger=DateTrigger())` -
PAS un job planifie recurrent comme ingest_prices_job/credit_dividends_job.
Meme pattern d'acces DB que les jobs existants (ouvre sa propre session,
AsyncSessionLocal) puisqu'il tourne hors du cycle de requete FastAPI.
"""
import logging
import uuid

from app.database import AsyncSessionLocal
from app.domains.llm_analyst import job_repository, service

logger = logging.getLogger(__name__)


async def run_llm_analysis_job(job_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        job = await job_repository.get_job(db, job_id)
        if job is None:
            logger.error("llm_analysis_job: job introuvable (id=%s)", job_id)
            return

        await job_repository.mark_running(db, job)
        try:
            result = await service.run_analysis(
                db, job.asset_id, job.strategy_name, job.period_start, job.period_end, job.model_name
            )
            await job_repository.mark_completed(db, job, result)
            logger.info(
                "llm_analysis_job termine: job=%s strategie=%s avertissements=%d",
                job_id,
                job.strategy_name,
                len(result.get("citation_warnings", [])),
            )
        except Exception as exc:
            logger.exception("llm_analysis_job: echec (job=%s)", job_id)
            await job_repository.mark_failed(db, job, str(exc))
