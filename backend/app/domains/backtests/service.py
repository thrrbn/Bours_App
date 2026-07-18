"""
Rejeu des signaux historiques contre les prix reels ulterieurs pour mesurer
la performance du moteur de score. Voir docs/02 (backtesting) et docs/10
(validation walk-forward, pas de fuite de donnees futures - un signal n'est
jamais compare qu'a des prix strictement posterieurs a son calcul).
"""
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_data.models import PriceBar
from app.domains.signals.models import Signal
from app.domains.signals.training import HORIZON_FORWARD_DAYS


@dataclass
class BacktestMetrics:
    precision: float
    win_rate: float
    false_positive_rate: float
    max_drawdown: float
    signal_count: int


def evaluate_signals(signal_outcomes: list[dict]) -> BacktestMetrics:
    """
    signal_outcomes: liste de dicts {"final_signal": str, "forward_return": float}
    ou forward_return est le rendement reellement observe N jours apres le signal.

    Regle de succes simplifiee V1 : un signal 'achat_speculatif' ou 'surveillance'
    est un succes si forward_return > 0 ; un signal 'prudence' ou 'vente_defensive'
    est un succes si forward_return <= 0 ; 'neutre' est toujours exclu du calcul.
    """
    evaluable = [s for s in signal_outcomes if s["final_signal"] != "neutre"]
    if not evaluable:
        return BacktestMetrics(0.0, 0.0, 0.0, 0.0, len(signal_outcomes))

    successes = 0
    false_positives = 0
    running_max = float("-inf")
    max_drawdown = 0.0
    cumulative = 1.0

    for outcome in evaluable:
        bullish_signal = outcome["final_signal"] in ("achat_speculatif", "surveillance")
        is_success = (outcome["forward_return"] > 0) == bullish_signal
        if is_success:
            successes += 1
        else:
            false_positives += 1

        cumulative *= (1 + outcome["forward_return"]) if bullish_signal else (1 - outcome["forward_return"])
        running_max = max(running_max, cumulative)
        drawdown = (running_max - cumulative) / running_max if running_max > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)

    precision = successes / len(evaluable)
    false_positive_rate = false_positives / len(evaluable)

    return BacktestMetrics(
        precision=round(precision, 4),
        win_rate=round(precision, 4),
        false_positive_rate=round(false_positive_rate, 4),
        max_drawdown=round(max_drawdown, 4),
        signal_count=len(signal_outcomes),
    )


async def _compute_forward_return(
    db: AsyncSession, asset_id: uuid.UUID, from_date: date, forward_days: int
) -> float | None:
    stmt = (
        select(PriceBar)
        .where(PriceBar.asset_id == asset_id, PriceBar.trade_date >= from_date)
        .order_by(PriceBar.trade_date.asc())
        .limit(forward_days + 1)
    )
    result = await db.execute(stmt)
    bars = list(result.scalars().all())
    if len(bars) < 2:
        return None
    start_price = float(bars[0].close)
    end_price = float(bars[-1].close)
    if start_price == 0:
        return None
    return (end_price - start_price) / start_price


async def run_backtest_for_asset(
    db: AsyncSession, asset_id: uuid.UUID, horizon: str, period_start: date, period_end: date
) -> BacktestMetrics:
    """
    Rejoue les signaux d'un actif/horizon sur une periode donnee : pour
    chaque signal, calcule le rendement reel qui a suivi, puis agrege via
    evaluate_signals(). Les signaux sans assez de prix futurs disponibles
    (trop recents) sont simplement exclus, pas traites comme un echec.
    """
    stmt = (
        select(Signal)
        .where(
            Signal.asset_id == asset_id,
            Signal.horizon == horizon,
            Signal.computed_at >= period_start,
            Signal.computed_at <= period_end,
        )
        .order_by(Signal.computed_at.asc())
    )
    result = await db.execute(stmt)
    signals = list(result.scalars().all())

    forward_days = HORIZON_FORWARD_DAYS.get(horizon, 5)
    outcomes = []
    for signal in signals:
        forward_return = await _compute_forward_return(db, asset_id, signal.computed_at.date(), forward_days)
        if forward_return is None:
            continue
        outcomes.append({"final_signal": signal.final_signal, "forward_return": forward_return})

    return evaluate_signals(outcomes)
