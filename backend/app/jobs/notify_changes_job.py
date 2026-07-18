"""Job planifie : verifie la watchlist et envoie un digest email si besoin.
Execute apres compute_signals_job (voir jobs/scheduler.py) pour disposer des
signaux frais du jour."""
import logging

from app.database import AsyncSessionLocal
from app.domains.notifications.service import check_and_notify_watchlist

logger = logging.getLogger(__name__)


async def notify_changes_job() -> None:
    async with AsyncSessionLocal() as db:
        try:
            change_count = await check_and_notify_watchlist(db)
            logger.info("notify_changes_job termine: %s changement(s)", change_count)
        except Exception:
            logger.exception("Echec de notify_changes_job")
