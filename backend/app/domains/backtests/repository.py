import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.backtests.models import BacktestResult, BacktestRun


async def create_run(
    db: AsyncSession, engine_version: str, period_start: date, period_end: date, asset_scope: dict
) -> BacktestRun:
    run = BacktestRun(
        engine_version=engine_version, period_start=period_start, period_end=period_end, asset_scope=asset_scope
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def save_result(
    db: AsyncSession,
    run_id: uuid.UUID,
    asset_id: uuid.UUID,
    horizon: str,
    *,
    precision: float | None,
    win_rate: float | None,
    false_positive_rate: float | None,
    max_drawdown: float | None,
    signal_count: int,
    sharpe_ratio: float | None = None,
    calmar_ratio: float | None = None,
    profit_factor: float | None = None,
    avg_risk_reward: float | None = None,
    strategy_name: str = "internal_rules",
    extra_metrics: dict | None = None,
    plot_html: str | None = None,
) -> BacktestResult:
    """
    Champs explicites plutot qu'un objet BacktestMetrics unique (31/07/2026) :
    les deux moteurs (interne evaluate_signals() et backtesting.py, voir
    kernc_engine.py) produisent des metriques compatibles mais pas le meme
    type d'objet - le routeur normalise en kwargs avant d'appeler cette
    fonction, qui reste ainsi agnostique du moteur d'origine. strategy_name
    distingue "internal_rules" (comportement par defaut, moteur historique)
    de "signal_replay"/"sma_cross"/"buy_and_hold" (nouveau moteur).
    """
    result = BacktestResult(
        backtest_run_id=run_id,
        asset_id=asset_id,
        horizon=horizon,
        precision=precision,
        win_rate=win_rate,
        false_positive_rate=false_positive_rate,
        max_drawdown=max_drawdown,
        signal_count=signal_count,
        sharpe_ratio=sharpe_ratio,
        calmar_ratio=calmar_ratio,
        profit_factor=profit_factor,
        avg_risk_reward=avg_risk_reward,
        strategy_name=strategy_name,
        extra_metrics=extra_metrics,
        plot_html=plot_html,
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)
    return result


async def get_results_for_run(db: AsyncSession, run_id: uuid.UUID) -> list[BacktestResult]:
    stmt = select(BacktestResult).where(BacktestResult.backtest_run_id == run_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
