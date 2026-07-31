import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AssetNotFoundError
from app.database import get_db
from app.domains.assets import repository as assets_repository
from app.domains.news import repository, service
from app.domains.news.providers.rss_provider import RssNewsProvider
from app.domains.news.schemas import (
    CustomKeywordCreate,
    CustomKeywordRead,
    KeywordMatchRead,
    NewsArticleRead,
    SentimentSummary,
)

router = APIRouter(prefix="/api/v1/news", tags=["news"])

# Instance unique du provider RSS (voir docs/08-pipeline-ingestion.md).
_provider = RssNewsProvider()


@router.get("/custom-keywords", response_model=list[CustomKeywordRead])
async def list_custom_keywords(db: AsyncSession = Depends(get_db)):
    """
    Mots-cles/opportunites personnalises, en plus du lexique fixe (voir
    nlp/lexicon.py) - liste GLOBALE (appliquee a tous les actifs suivis), pris
    en compte au prochain rafraichissement des news (POST /news/{id}/refresh
    ou /news/refresh-all) et dans le briefing quotidien (voir
    /notifications/briefing/preview).
    """
    return await service.list_custom_keywords(db)


@router.post("/custom-keywords", response_model=CustomKeywordRead, status_code=201)
async def add_custom_keyword(payload: CustomKeywordCreate, db: AsyncSession = Depends(get_db)):
    return await service.add_custom_keyword(db, payload.keyword, payload.weight, payload.horizon_impact)


@router.delete("/custom-keywords/{keyword_id}", status_code=204)
async def delete_custom_keyword(keyword_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await service.delete_custom_keyword(db, keyword_id)


@router.post("/rescan-keywords")
async def rescan_keywords(asset_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    """
    Repasse les articles DEJA en base (aucun nouvel appel RSS) au lexique
    actuel (fixe + mots-cles personnalises) - a utiliser apres avoir ajoute
    un mot-cle pour qu'il s'applique retroactivement aux articles deja
    connus (voir service.py::rescan_keywords). Sans asset_id : rescanne TOUS
    les articles.
    """
    return await service.rescan_keywords(db, asset_id=asset_id)


@router.get("/keyword-matches", response_model=list[KeywordMatchRead])
async def get_keyword_matches(keyword: str | None = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    Articles (toutes dates, tous actifs) qui matchent un mot-cle
    PERSONNALISE (voir service.py::get_keyword_matches) - reponse a "ou
    est-ce que ca apparait" pour un mot-cle ajoute (POST /custom-keywords).
    Sans `keyword` : tous les mots-cles personnalises actuellement definis.
    Route declaree avant /{asset_id} pour eviter que FastAPI n'essaie de
    parser "keyword-matches" comme un UUID.
    """
    return await service.get_keyword_matches(db, keyword=keyword, limit=limit)


@router.get("/keyword-matches/summary", response_model=list[str])
async def get_keyword_matches_summary(max_lines: int = 10, db: AsyncSession = Depends(get_db)):
    """
    Resume en francais des correspondances de mots-cles personnalises, une
    ligne par mot-cle, plafonne a `max_lines` (voir service.py::
    get_keyword_matches_summary). Route declaree avant /{asset_id}.
    """
    return await service.get_keyword_matches_summary(db, max_lines=max_lines)


@router.get("/articles/{article_id}/summary", response_model=list[str])
async def summarize_article(article_id: uuid.UUID, max_lines: int = 10, db: AsyncSession = Depends(get_db)):
    """
    Resume en francais d'un article precis, plafonne a `max_lines` - voir
    service.py::summarize_article pour la limite honnete (pas de texte
    integral, uniquement ce que fournit deja le flux RSS).
    """
    return await service.summarize_article(db, article_id, max_lines=max_lines)


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
