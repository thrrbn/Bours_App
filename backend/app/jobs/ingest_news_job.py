"""Job d'ingestion des news - reutilise le service news, aucune logique dupliquee."""
import logging

from app.database import AsyncSessionLocal
from app.domains.assets.repository import list_all as list_all_assets
from app.domains.news.providers.rss_provider import RssNewsProvider
from app.domains.news.service import ingest_and_score

logger = logging.getLogger(__name__)
provider = RssNewsProvider()


async def ingest_news_job() -> dict:
    async with AsyncSessionLocal() as db:
        assets = await list_all_assets(db)
        errors = 0
        total_new = 0
        for asset in assets:
            try:
                total_new += await ingest_and_score(db, asset.id, asset.ticker, asset.name, provider)
            except Exception:
                errors += 1
                logger.exception("Echec ingestion news pour %s", asset.ticker)
        logger.info("ingest_news_job termine: %s nouveaux articles, %s erreurs", total_new, errors)
        return {"total_assets": len(assets), "new_articles": total_new, "errors": errors}
