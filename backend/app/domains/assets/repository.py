"""Acces aux donnees de l'actif - requetes SQL/ORM pures, aucune logique metier ici."""
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.assets.models import Asset
from app.domains.assets.schemas import AssetCreate


async def get_by_id(db: AsyncSession, asset_id: uuid.UUID) -> Asset | None:
    return await db.get(Asset, asset_id)


async def get_by_ticker(db: AsyncSession, ticker: str, market: str) -> Asset | None:
    result = await db.execute(select(Asset).where(Asset.ticker == ticker, Asset.market == market))
    return result.scalar_one_or_none()


async def search(db: AsyncSession, query: str, limit: int = 20) -> list[Asset]:
    pattern = f"%{query.upper()}%"
    stmt = (
        select(Asset)
        .where(or_(Asset.ticker.ilike(pattern), Asset.name.ilike(pattern)))
        .where(Asset.is_active.is_(True))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_all(db: AsyncSession, market: str | None = None, sector: str | None = None) -> list[Asset]:
    stmt = select(Asset).where(Asset.is_active.is_(True))
    if market:
        stmt = stmt.where(Asset.market == market)
    if sector:
        stmt = stmt.where(Asset.sector == sector)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create(db: AsyncSession, payload: AssetCreate) -> Asset:
    asset = Asset(**payload.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset
