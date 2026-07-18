"""Job quotidien d'ingestion des prix - reutilise le service market_data, aucune logique dupliquee."""
import logging

from app.database import AsyncSessionLocal
from app.domains.assets.repository import list_all as list_all_assets
from app.domains.market_data.providers.yahoo_finance import YahooFinanceProvider
from app.domains.market_data.service import compute_and_store_indicators, ingest_history

logger = logging.getLogger(__name__)
provider = YahooFinanceProvider()


async def ingest_prices_job() -> dict:
    async with AsyncSessionLocal() as db:
        assets = await list_all_assets(db)
        errors = 0
        for asset in assets:
            try:
                await ingest_history(db, asset.id, asset.ticker, provider)
                await compute_and_store_indicators(db, asset.id)
            except Exception:
                errors += 1
                logger.exception("Echec ingestion prix pour %s", asset.ticker)
        logger.info("ingest_prices_job termine: %s actifs traites, %s erreurs", len(assets), errors)
        return {"total_assets": len(assets), "errors": errors}
