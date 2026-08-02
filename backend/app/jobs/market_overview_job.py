"""Job planifie : rafraichit la page Marche (indices + top hausses/baisses
FR/US/crypto, toutes sources externes en direct - voir
market_overview/provider.py). 3 executions par jour (7h, 12h, 17h - voir
scheduler.py)."""
import logging

from app.database import AsyncSessionLocal
from app.domains.market_overview.service import refresh_snapshot

logger = logging.getLogger(__name__)


async def market_overview_job() -> None:
    async with AsyncSessionLocal() as db:
        try:
            snapshot = await refresh_snapshot(db)
            counts = {
                key: len(bucket.get("gainers", [])) + len(bucket.get("losers", []))
                for key, bucket in snapshot.movers.items()
            }
            logger.info(
                "market_overview_job termine: %d indice(s), mouvements %s",
                len(snapshot.indices),
                counts,
            )
        except Exception:
            logger.exception("Echec de market_overview_job")
