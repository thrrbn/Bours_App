import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AssetNotFoundError
from app.database import get_db
from app.domains.assets import repository as assets_repository
from app.domains.market_data import repository
from app.domains.market_data.schemas import HistoricalTrendRead, PriceBarRead, TechnicalIndicatorRead
from app.domains.market_data.service import (
    compute_and_store_indicators,
    compute_historical_trend,
    ingest_history,
    provider_for_market,
)

router = APIRouter(prefix="/api/v1/market-data", tags=["market_data"])


@router.get("/{asset_id}/prices", response_model=list[PriceBarRead])
async def get_prices(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    bars = await repository.get_price_history(db, asset_id)
    return list(reversed(bars))


@router.get("/{asset_id}/indicators", response_model=TechnicalIndicatorRead | None)
async def get_latest_indicators(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await repository.get_latest_indicators(db, asset_id)


@router.get("/{asset_id}/historical-trend", response_model=HistoricalTrendRead)
async def get_historical_trend(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Rendement reel passe (1/3/6/12 mois) - jamais une prediction, voir
    service.compute_historical_trend."""
    return await compute_historical_trend(db, asset_id)


@router.post("/refresh-all")
async def refresh_all_market_data(db: AsyncSession = Depends(get_db)):
    """
    Meme logique que /refresh mais pour tous les actifs connus en une seule
    requete - evite de devoir appeler /refresh un par un pour chaque valeur
    (utile juste apres avoir ajoute plusieurs actifs d'un coup, ex. seed BEL20).
    """
    assets = await assets_repository.list_all(db)
    results = []
    errors = 0
    for asset in assets:
        provider, source = provider_for_market(asset.market)
        try:
            bars_ingested = await ingest_history(db, asset.id, asset.ticker, provider, source=source)
            indicators_computed = await compute_and_store_indicators(db, asset.id)
            results.append(
                {"ticker": asset.ticker, "bars_ingested": bars_ingested, "indicators_computed": indicators_computed}
            )
        except Exception as exc:
            errors += 1
            results.append({"ticker": asset.ticker, "error": str(exc)})
    return {"total_assets": len(assets), "errors": errors, "details": results}


@router.post("/{asset_id}/refresh")
async def refresh_market_data(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Force une ingestion immediate des prix (Yahoo Finance pour les actions/ETF,
    Binance pour les actifs de marche "BINANCE") et un recalcul des indicateurs
    techniques pour cet actif, sans attendre le job planifie quotidien
    (docs/14-jobs-planifies.md). Utile en developpement/debug pour tester le
    pipeline sans attendre 06:00.
    """
    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))

    provider, source = provider_for_market(asset.market)
    bars_ingested = await ingest_history(db, asset.id, asset.ticker, provider, source=source)
    indicators_computed = await compute_and_store_indicators(db, asset.id)
    latest_bar = await repository.get_latest_bar(db, asset_id)

    return {
        "asset_id": str(asset_id),
        "ticker": asset.ticker,
        "bars_ingested": bars_ingested,
        "indicators_computed": indicators_computed,
        "latest_trade_date": latest_bar.trade_date if latest_bar else None,
    }
