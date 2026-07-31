"""Job planifie : construit et envoie le briefing quotidien (portefeuille
virtuel + watchlist, voir notifications/briefing_service.py). Execute apres
compute_signals_job (7h) et refresh_analyst_ratings_job (6h30, voir
jobs/scheduler.py) pour disposer de signaux et d'un consensus frais du jour -
ne recalcule rien lui-meme, uniquement une lecture/synthese."""
import logging

from app.database import AsyncSessionLocal
from app.domains.notifications.briefing_service import send_daily_briefing

logger = logging.getLogger(__name__)


async def daily_briefing_job() -> None:
    async with AsyncSessionLocal() as db:
        try:
            briefing = await send_daily_briefing(db)
            logger.info("daily_briefing_job termine: %s titre(s) dans le briefing", len(briefing.items))
        except Exception:
            logger.exception("Echec de daily_briefing_job")
