"""Logique metier du domaine assets : recherche, normalisation, resolution de marche."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AssetNotFoundError
from app.domains.assets import repository
from app.domains.assets.models import Asset
from app.domains.assets.schemas import AssetCreate


async def get_asset_or_raise(db: AsyncSession, asset_id: uuid.UUID) -> Asset:
    asset = await repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))
    return asset


async def search_assets(db: AsyncSession, query: str) -> list[Asset]:
    normalized = query.strip()
    if not normalized:
        return []
    return await repository.search(db, normalized)


async def list_assets(db: AsyncSession, market: str | None, sector: str | None) -> list[Asset]:
    return await repository.list_all(db, market=market, sector=sector)


async def create_asset(db: AsyncSession, payload: AssetCreate) -> Asset:
    existing = await repository.get_by_ticker(db, payload.ticker, payload.market)
    if existing is not None:
        return existing
    return await repository.create(db, payload)
