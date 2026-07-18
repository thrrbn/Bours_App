import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.backtests import repository, service
from app.domains.backtests.schemas import BacktestResultRead, BacktestRunCreate

router = APIRouter(prefix="/api/v1/backtests", tags=["backtests"])

HORIZONS = ("short", "medium", "long")


@router.post("/run")
async def run_backtest(payload: BacktestRunCreate, db: AsyncSession = Depends(get_db)):
    """
    Cree un run de backtest et calcule reellement les metriques (precision,
    win rate, faux positifs, drawdown) pour chaque actif/horizon du scope,
    en rejouant les signaux historiques contre les prix reels qui ont suivi.
    """
    run = await repository.create_run(
        db,
        engine_version=payload.engine_version,
        period_start=payload.period_start,
        period_end=payload.period_end,
        asset_scope={"asset_ids": [str(a) for a in payload.asset_ids]},
    )

    for asset_id in payload.asset_ids:
        for horizon in HORIZONS:
            metrics = await service.run_backtest_for_asset(
                db, asset_id, horizon, payload.period_start, payload.period_end
            )
            if metrics.signal_count == 0:
                continue
            await repository.save_result(db, run.id, asset_id, horizon, metrics)

    return {"backtest_run_id": run.id, "status": "completed"}


@router.get("/{run_id}", response_model=list[BacktestResultRead])
async def get_backtest_results(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await repository.get_results_for_run(db, run_id)
