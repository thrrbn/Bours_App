import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AssetNotFoundError
from app.database import get_db
from app.domains.assets import repository as assets_repository
from app.domains.news import repository, service
from app.domains.news.providers.rss_provider import RssNewsProvider
from app.domains.news.schemas import NewsArticleRead, SentimentSummary

router = APIRouter(prefix="/api/v1/news", tags=["news"])

# Instance unique du provider RSS (voir docs/08-pipeline-ingestion.md).
_provider = RssNewsProvider()


@router.get("/{asset_id}", response_model=list[NewsArticleRead])
async def get_news(asset_id: uuid.UUID, days: int = 7, db: AsyncSession = Depends(get_db)):
    return await repository.get_recent_articles(db, asset_id, days=days)


@router.get("/{asset_id}/sentiment-summary", response_model=SentimentSummary)
async def get_sentiment_summary(asset_id: uuid.UUID, days: int = 7, db: AsyncSession = Depends(get_db)):
    return await service.get_sentiment_summary(db, asset_id, days=days)


@router.post("/refresh-all")
async def refresh_all_news(db: AsyncSession = Depends(get_db)):
    """Meme logique que /refresh mais pour tous les actifs connus d'un coup."""
    assets = await assets_repository.list_all(db)
    total_new = 0
    errors = 0
    for asset in assets:
        try:
            total_new += await service.ingest_and_score(db, asset.id, asset.ticker, asset.name, _provider)
        except Exception:
            errors += 1
    return {"total_assets": len(assets), "new_articles_ingested": total_new, "errors": errors}


@router.post("/{asset_id}/refresh")
async def refresh_news(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Force une ingestion immediate des flux RSS (Yahoo Finance + Google News)
    pour cet actif, sans attendre le job planifie (docs/14-jobs-planifies.md).
    Utile en developpement/debug pour tester le pipeline NLP sans attendre.
    """
    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))

    new_articles = await service.ingest_and_score(db, asset.id, asset.ticker, asset.name, _provider)

    return {
        "asset_id": str(asset_id),
        "ticker": asset.ticker,
        "new_articles_ingested": new_articles,
    }
