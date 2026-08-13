"""
Job quotidien du scorecard de fiabilite reelle (13/08/2026, voir
app/domains/signal_reliability/service.py) - evalue les signaux reels arrives
a maturite (leur horizon de rendement futur est ecoule) et jamais encore
evalues, les insere dans signal_outcomes. Idempotent (voir unicite de
signal_id) : peut etre relance sans dupliquer.
"""
import logging

from app.database import AsyncSessionLocal
from app.domains.signal_reliability.service import evaluate_pending_outcomes

logger = logging.getLogger(__name__)


async def evaluate_signal_outcomes_job() -> dict:
    async with AsyncSessionLocal() as db:
        summary = await evaluate_pending_outcomes(db)
        total_evaluated = sum(h["evaluated"] for h in summary.values())
        logger.info("evaluate_signal_outcomes_job termine: %s signaux evalues (%s)", total_evaluated, summary)
        return summary
