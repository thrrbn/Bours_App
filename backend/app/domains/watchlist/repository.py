"""Acces aux donnees de la watchlist - requetes SQL/ORM pures."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.watchlist.models import WatchlistItem


async def list_all(db: AsyncSession) -> list[WatchlistItem]:
    stmt = select(WatchlistItem).options(selectinload(WatchlistItem.asset)).order_by(WatchlistItem.added_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_by_asset_id(db: AsyncSession, asset_id: uuid.UUID) -> WatchlistItem | None:
    result = await db.execute(select(WatchlistItem).where(WatchlistItem.asset_id == asset_id))
    return result.scalar_one_or_none()


async def add(db: AsyncSession, asset_id: uuid.UUID, notify_on_change: bool) -> WatchlistItem:
    item = WatchlistItem(asset_id=asset_id, notify_on_change=notify_on_change)
    db.add(item)
    await db.commit()
    await db.refresh(item, attribute_names=["asset"])
    return item


async def remove(db: AsyncSession, item: WatchlistItem) -> None:
    await db.delete(item)
    await db.commit()
