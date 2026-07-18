"""Persistance des signaux et de leurs explications."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.signals.models import Signal, SignalExplanation
from app.domains.signals.models_ml.baseline_rules import SignalResult


async def save_signal(db: AsyncSession, asset_id: uuid.UUID, horizon: str, result: SignalResult) -> Signal:
    signal = Signal(
        asset_id=asset_id,
        horizon=horizon,
        technical_score=result.technical_score,
        news_score=result.news_score,
        risk_score=result.risk_score,
        confidence_score=result.confidence_score,
        final_signal=result.final_signal,
        engine_version=result.engine_version,
    )
    db.add(signal)
    await db.flush()

    for component in result.components:
        db.add(
            SignalExplanation(
                signal_id=signal.id,
                component=component.name,
                contribution_pct=component.contribution_pct,
                text_explanation=component.explanation,
                supporting_data=component.supporting_data,
            )
        )
    await db.commit()
    await db.refresh(signal)
    return signal


async def get_latest_signal(db: AsyncSession, asset_id: uuid.UUID, horizon: str) -> Signal | None:
    stmt = (
        select(Signal)
        .where(Signal.asset_id == asset_id, Signal.horizon == horizon)
        .order_by(Signal.computed_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_explanations(db: AsyncSession, signal_id: uuid.UUID) -> list[SignalExplanation]:
    stmt = select(SignalExplanation).where(SignalExplanation.signal_id == signal_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_signal_history(db: AsyncSession, asset_id: uuid.UUID, horizon: str, limit: int = 90) -> list[Signal]:
    stmt = (
        select(Signal)
        .where(Signal.asset_id == asset_id, Signal.horizon == horizon)
        .order_by(Signal.computed_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
