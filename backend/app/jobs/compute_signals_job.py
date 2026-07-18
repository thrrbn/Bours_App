"""Job de calcul des signaux - reutilise le service signals pour les 3 horizons."""
import logging

from app.database import AsyncSessionLocal
from app.domains.assets.repository import list_all as list_all_assets
from app.domains.signals.service import compute_signal_for_asset

logger = logging.getLogger(__name__)
HORIZONS = ("short", "medium", "long")


async def compute_signals_job() -> dict:
    async with AsyncSessionLocal() as db:
        assets = await list_all_assets(db)
        errors = 0
        for asset in assets:
            for horizon in HORIZONS:
                try:
                    await compute_signal_for_asset(db, asset.id, horizon)
                except Exception:
                    errors += 1
                    logger.exception("Echec calcul signal %s/%s", asset.ticker, horizon)
        logger.info(
            "compute_signals_job termine: %s actifs x %s horizons, %s erreurs", len(assets), len(HORIZONS), errors
        )
        return {"total_assets": len(assets), "horizons": len(HORIZONS), "errors": errors}
