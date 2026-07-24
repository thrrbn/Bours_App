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


async def save_result(db: AsyncSession, run_id: uuid.UUID, asset_id: uuid.UUID, horizon: str, metrics) -> BacktestResult:
    result = BacktestResult(
        backtest_run_id=run_id,
        asset_id=asset_id,
        horizon=horizon,
        precision=metrics.precision,
        win_rate=metrics.win_rate,
        false_positive_rate=metrics.false_positive_rate,
        max_drawdown=metrics.max_drawdown,
        signal_count=metrics.signal_count,
        sharpe_ratio=metrics.sharpe_ratio,
        calmar_ratio=metrics.calmar_ratio,
        profit_factor=metrics.profit_factor,
        avg_risk_reward=metrics.avg_risk_reward,
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)
    return result


async def get_results_for_run(db: AsyncSession, run_id: uuid.UUID) -> list[BacktestResult]:
    stmt = select(BacktestResult).where(BacktestResult.backtest_run_id == run_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
