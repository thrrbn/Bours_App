import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.models import NotificationState


async def get_state(db: AsyncSession, asset_id: uuid.UUID, horizon: str) -> NotificationState | None:
    stmt = select(NotificationState).where(
        NotificationState.asset_id == asset_id, NotificationState.horizon == horizon
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_state(db: AsyncSession, asset_id: uuid.UUID, horizon: str, final_signal: str) -> None:
    existing = await get_state(db, asset_id, horizon)
    if existing is None:
        db.add(NotificationState(asset_id=asset_id, horizon=horizon, last_notified_signal=final_signal))
    else:
        existing.last_notified_signal = final_signal
    await db.commit()
