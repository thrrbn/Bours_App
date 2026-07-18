import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.analyst.models import AnalystConsensus


async def get_by_asset(db: AsyncSession, asset_id: uuid.UUID) -> AnalystConsensus | None:
    stmt = select(AnalystConsensus).where(AnalystConsensus.asset_id == asset_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession) -> list[AnalystConsensus]:
    stmt = select(AnalystConsensus).options(selectinload(AnalystConsensus.asset))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def upsert(
    db: AsyncSession,
    asset_id: uuid.UUID,
    strong_buy: int,
    buy: int,
    hold: int,
    sell: int,
    strong_sell: int,
    consensus_score: float,
    consensus_label: str,
) -> AnalystConsensus:
    existing = await get_by_asset(db, asset_id)
    if existing is None:
        existing = AnalystConsensus(asset_id=asset_id)
        db.add(existing)

    existing.strong_buy = strong_buy
    existing.buy = buy
    existing.hold = hold
    existing.sell = sell
    existing.strong_sell = strong_sell
    existing.consensus_score = consensus_score
    existing.consensus_label = consensus_label

    await db.commit()
    await db.refresh(existing, attribute_names=["asset"])
    return existing
