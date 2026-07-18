"""Acces aux donnees de marche - upserts idempotents, aucune logique metier."""
import uuid

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_data.models import PriceBar, TechnicalIndicator
from app.domains.market_data.providers.base import PriceBarDTO


async def upsert_price_bars(db: AsyncSession, asset_id: uuid.UUID, bars: list[PriceBarDTO]) -> None:
    if not bars:
        return
    values = [
        {
            "asset_id": asset_id,
            "trade_date": bar.trade_date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "adjusted_close": bar.adjusted_close,
            "volume": bar.volume,
        }
        for bar in bars
    ]
    stmt = insert(PriceBar).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["asset_id", "trade_date"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "adjusted_close": stmt.excluded.adjusted_close,
            "volume": stmt.excluded.volume,
        },
    )
    await db.execute(stmt)
    await db.commit()


async def get_price_history(db: AsyncSession, asset_id: uuid.UUID, limit: int = 400) -> list[PriceBar]:
    stmt = (
        select(PriceBar)
        .where(PriceBar.asset_id == asset_id)
        .order_by(PriceBar.trade_date.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_latest_bar(db: AsyncSession, asset_id: uuid.UUID) -> PriceBar | None:
    """Dernier cours connu - utilise par le portefeuille virtuel (Etape 12) pour
    valoriser les positions et executer les achats/ventes simules."""
    stmt = select(PriceBar).where(PriceBar.asset_id == asset_id).order_by(PriceBar.trade_date.desc()).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_latest_indicators(db: AsyncSession, asset_id: uuid.UUID) -> TechnicalIndicator | None:
    stmt = (
        select(TechnicalIndicator)
        .where(TechnicalIndicator.asset_id == asset_id)
        .order_by(TechnicalIndicator.trade_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # exclut NaN


async def upsert_indicators(db: AsyncSession, asset_id: uuid.UUID, indicators_df: pd.DataFrame) -> None:
    values = []
    for trade_date, row in indicators_df.iterrows():
        values.append(
            {
                "asset_id": asset_id,
                "trade_date": trade_date,
                "sma_20": _safe_float(row.get("sma_20")),
                "sma_50": _safe_float(row.get("sma_50")),
                "sma_200": _safe_float(row.get("sma_200")),
                "ema_12": _safe_float(row.get("ema_12")),
                "ema_26": _safe_float(row.get("ema_26")),
                "rsi_14": _safe_float(row.get("rsi_14")),
                "macd": _safe_float(row.get("macd")),
                "macd_signal": _safe_float(row.get("macd_signal")),
                "bollinger_upper": _safe_float(row.get("bollinger_upper")),
                "bollinger_lower": _safe_float(row.get("bollinger_lower")),
                "volatility_20d": _safe_float(row.get("volatility_20d")),
                "momentum_roc_20": _safe_float(row.get("momentum_roc_20")),
            }
        )
    if not values:
        return
    stmt = insert(TechnicalIndicator).values(values)
    update_cols = {c: stmt.excluded[c] for c in values[0] if c not in ("asset_id", "trade_date")}
    stmt = stmt.on_conflict_do_update(index_elements=["asset_id", "trade_date"], set_=update_cols)
    await db.execute(stmt)
    await db.commit()
