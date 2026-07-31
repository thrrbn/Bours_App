"""Acces aux donnees briefing_asset_states - requetes SQL/ORM pures."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.briefing_models import BriefingAssetState


async def get_all_states(db: AsyncSession) -> dict[tuple[uuid.UUID, str], str]:
    """Tous les etats en UNE requete (asset_id, horizon) -> last_signal - evite
    un aller-retour DB par actif x horizon lors de la construction du
    briefing (meme principe anti-N+1 que get_status_overview, voir
    assets/service.py)."""
    result = await db.execute(select(BriefingAssetState.asset_id, BriefingAssetState.horizon, BriefingAssetState.last_signal))
    return {(asset_id, horizon): last_signal for asset_id, horizon, last_signal in result.all()}


async def upsert_state(db: AsyncSession, asset_id: uuid.UUID, horizon: str, last_signal: str) -> None:
    stmt = select(BriefingAssetState).where(
        BriefingAssetState.asset_id == asset_id, BriefingAssetState.horizon == horizon
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is None:
        db.add(BriefingAssetState(asset_id=asset_id, horizon=horizon, last_signal=last_signal))
    else:
        existing.last_signal = last_signal
    await db.commit()
