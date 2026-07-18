import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.signals import repository, service
from app.domains.signals.schemas import SignalRead

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


@router.get("/{asset_id}", response_model=SignalRead)
async def get_signal(
    asset_id: uuid.UUID,
    horizon: str = Query("short", pattern="^(short|medium|long)$"),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_or_compute_signal(db, asset_id, horizon)


@router.post("/{asset_id}/recompute", response_model=SignalRead)
async def recompute_signal(
    asset_id: uuid.UUID,
    horizon: str = Query("short", pattern="^(short|medium|long)$"),
    db: AsyncSession = Depends(get_db),
):
    return await service.compute_signal_for_asset(db, asset_id, horizon)


@router.get("/{asset_id}/history")
async def get_signal_history(
    asset_id: uuid.UUID,
    horizon: str = Query("short", pattern="^(short|medium|long)$"),
    db: AsyncSession = Depends(get_db),
):
    history = await repository.get_signal_history(db, asset_id, horizon)
    return [
        {
            "computed_at": s.computed_at,
            "final_signal": s.final_signal,
            "technical_score": float(s.technical_score),
            "news_score": float(s.news_score),
            "risk_score": float(s.risk_score),
            "confidence_score": float(s.confidence_score),
        }
        for s in history
    ]
