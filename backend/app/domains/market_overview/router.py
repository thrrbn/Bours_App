from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.market_overview import service
from app.domains.market_overview.schemas import MarketSnapshotRead

router = APIRouter(prefix="/api/v1/market-overview", tags=["market-overview"])

_EMPTY_SNAPSHOT = {
    "captured_at": None,
    "indices": [],
    "movers": {
        "FR": {"gainers": [], "losers": []},
        "US": {"gainers": [], "losers": []},
        "CRYPTO": {"gainers": [], "losers": []},
    },
}


@router.get("")
async def read_latest(db: AsyncSession = Depends(get_db)):
    """Dernier instantane connu - ne declenche AUCUN appel Yahoo Finance (voir
    /refresh) : lecture pure de ce que le job planifie 3x/jour a deja
    persiste. Renvoie une structure vide (pas une 404) tant qu'aucun
    rafraichissement n'a encore eu lieu, pour simplifier le rendu cote
    frontend au tout premier demarrage de l'app."""
    snapshot = await service.get_latest(db)
    if snapshot is None:
        return _EMPTY_SNAPSHOT
    return MarketSnapshotRead.model_validate(snapshot)


@router.post("/refresh", response_model=MarketSnapshotRead)
async def trigger_refresh(db: AsyncSession = Depends(get_db)):
    """Declenchement manuel (bouton "Actualiser" cote frontend) - le meme
    code que le job planifie (voir jobs/market_overview_job.py), rejouable a
    la demande entre deux horaires fixes."""
    return await service.refresh_snapshot(db)
