import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.backtests import kernc_engine, repository, service
from app.domains.backtests.schemas import BacktestKerncRunCreate, BacktestResultRead, BacktestRunCreate
from app.domains.signals.models_ml.baseline_rules import DecisionParams

router = APIRouter(prefix="/api/v1/backtests", tags=["backtests"])

HORIZONS = ("short", "medium", "long")

try:
    import backtesting as _backtesting_lib

    _KERNC_VERSION = getattr(_backtesting_lib, "__version__", "unknown")
except ImportError:  # pragma: no cover - la dependance est dans requirements.txt
    _KERNC_VERSION = "unknown"


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
            await repository.save_result(
                db,
                run.id,
                asset_id,
                horizon,
                precision=metrics.precision,
                win_rate=metrics.win_rate,
                false_positive_rate=metrics.false_positive_rate,
                max_drawdown=metrics.max_drawdown,
                signal_count=metrics.signal_count,
                sharpe_ratio=metrics.sharpe_ratio,
                calmar_ratio=metrics.calmar_ratio,
                profit_factor=metrics.profit_factor,
                avg_risk_reward=metrics.avg_risk_reward,
                strategy_name="internal_rules",
            )

    return {"backtest_run_id": run.id, "status": "completed"}


@router.post("/run-kernc")
async def run_backtest_kernc(payload: BacktestKerncRunCreate, db: AsyncSession = Depends(get_db)):
    """
    Meme scope (actifs + periode) que /run, mais via backtesting.py (31/07/2026,
    voir kernc_engine.py) : simulation reelle bar-par-bar (cash, ordres,
    equity curve), au lieu du rejeu analytique de signaux du moteur interne.

    Ecrit dans les MEMES tables que /run (engine_version distinct ->
    "backtesting.py-{version}"), avec un strategy_name par ligne :
    - signal_replay : rejoue nos propres signaux stockes, un run par horizon
      (short/medium/long), comme le moteur interne.
    - sma_cross / buy_and_hold : benchmarks classiques, independants de
      l'horizon (horizon stocke a "n/a" par convention).

    Permet de comparer les deux moteurs cote a cote pour un meme actif/
    periode via GET /{run_id} (les deux runs restent distincts, un run_id
    different par POST).

    Laboratoire de parametres (31/07/2026, voir schemas.py et kernc_engine.py) :
    `sma_params` (n1/n2) et `decision_params` (seuils/ponderation de decision)
    sont optionnels - omis, comportement identique a avant. Fournis, ils ne
    testent QUE ce run-la (rien de sauvegarde, rien qui affecte le moteur de
    signal reel) ; les valeurs effectivement utilisees sont toujours
    consignees dans `extra_metrics._params_used` de chaque resultat pour
    rester lisibles en comparant plusieurs run_id entre eux.
    """
    run = await repository.create_run(
        db,
        engine_version=f"backtesting.py-{_KERNC_VERSION}",
        period_start=payload.period_start,
        period_end=payload.period_end,
        asset_scope={"asset_ids": [str(a) for a in payload.asset_ids]},
    )

    decision_params = (
        DecisionParams(**payload.decision_params.model_dump()) if payload.decision_params is not None else None
    )

    for asset_id in payload.asset_ids:
        for strategy_name in kernc_engine.ALL_STRATEGIES:
            horizons = HORIZONS if strategy_name == kernc_engine.STRATEGY_SIGNAL_REPLAY else ("n/a",)
            for horizon in horizons:
                result = await kernc_engine.run_kernc_backtest(
                    db,
                    asset_id,
                    strategy_name,
                    payload.period_start,
                    payload.period_end,
                    horizon=horizon if horizon != "n/a" else "medium",
                    sma_n1=payload.sma_params.n1 if payload.sma_params else None,
                    sma_n2=payload.sma_params.n2 if payload.sma_params else None,
                    decision_params=decision_params,
                )
                if result is None:
                    continue
                await repository.save_result(
                    db,
                    run.id,
                    asset_id,
                    horizon,
                    precision=result["precision"],
                    win_rate=result["win_rate"],
                    false_positive_rate=result["false_positive_rate"],
                    max_drawdown=result["max_drawdown"],
                    signal_count=result["signal_count"],
                    sharpe_ratio=result["sharpe_ratio"],
                    calmar_ratio=result["calmar_ratio"],
                    profit_factor=result["profit_factor"],
                    avg_risk_reward=result["avg_risk_reward"],
                    strategy_name=result["strategy_name"],
                    extra_metrics=result["extra_metrics"],
                    plot_html=result["plot_html"],
                )

    return {"backtest_run_id": run.id, "status": "completed"}


@router.get("/{run_id}", response_model=list[BacktestResultRead])
async def get_backtest_results(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await repository.get_results_for_run(db, run_id)
