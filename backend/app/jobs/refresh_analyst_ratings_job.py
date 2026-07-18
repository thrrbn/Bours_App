"""Job planifie : rafraichit le consensus d'analystes externes pour tous les
actifs connus. Tolerant par actif - l'absence de couverture (frequent sur les
valeurs europeennes) n'est jamais une erreur, voir analyst/service.py."""
import logging

from app.database import AsyncSessionLocal
from app.domains.analyst.service import refresh_for_asset
from app.domains.assets.repository import list_all as list_all_assets

logger = logging.getLogger(__name__)


async def refresh_analyst_ratings_job() -> dict:
    async with AsyncSessionLocal() as db:
        assets = await list_all_assets(db)
        covered = 0
        errors = 0
        for asset in assets:
            try:
                result = await refresh_for_asset(db, asset.id)
                if result is not None:
                    covered += 1
            except Exception:
                errors += 1
                logger.exception("Echec rafraichissement consensus analystes %s", asset.ticker)
        logger.info(
            "refresh_analyst_ratings_job termine: %s/%s actifs couverts, %s erreurs",
            covered,
            len(assets),
            errors,
        )
        return {"total_assets": len(assets), "covered": covered, "errors": errors}
