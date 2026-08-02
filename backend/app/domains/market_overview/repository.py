"""Acces aux donnees market_snapshots - requetes SQL/ORM pures, aucune logique metier ici."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_overview.models import MarketSnapshot


async def save_snapshot(db: AsyncSession, indices: list[dict], movers: dict) -> MarketSnapshot:
    snapshot = MarketSnapshot(indices=indices, movers=movers)
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def get_latest_snapshot(db: AsyncSession) -> MarketSnapshot | None:
    stmt = select(MarketSnapshot).order_by(MarketSnapshot.captured_at.desc()).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
