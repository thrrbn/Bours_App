import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.backtests.models import BacktestResult, BacktestRun


async def create_run(
    db: AsyncSession,
    engine_version: str,
    period_start: date,
    period_end: date,
    asset_scope: dict,
    run_kind: str = "manual",
) -> BacktestRun:
    run = BacktestRun(
        engine_version=engine_version,
        period_start=period_start,
        period_end=period_end,
        asset_scope=asset_scope,
        run_kind=run_kind,
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


async def get_scheduled_results(db: AsyncSession, since=None) -> list[BacktestResult]:
    """
    13/08/2026 (scorecard de fiabilite par strategie) : resultats des runs
    AUTOMATIQUES uniquement (run_kind="scheduled_strategy_eval", voir
    jobs/evaluate_strategies_job.py) - jamais des tests ad-hoc de
    l'utilisateur (parametres variables d'un test a l'autre, inutilisables
    pour une moyenne). Inclut, depuis le 14/08/2026, les profils predefinis
    prudent/agressif en plus du profil par defaut (strategy_name suffixe,
    voir DECISION_PROFILES) - ce sont toujours des parametres FIXES reevalues
    chaque semaine, pas des tests ponctuels de l'utilisateur. `since`
    optionnel filtre sur BacktestRun.created_at (la date du RUN, pas du
    resultat individuel) pour les fenetres glissantes.
    """
    stmt = (
        select(BacktestResult)
        .join(BacktestRun, BacktestResult.backtest_run_id == BacktestRun.id)
        .where(BacktestRun.run_kind == "scheduled_strategy_eval")
    )
    if since is not None:
        stmt = stmt.where(BacktestRun.created_at >= since)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_last_scheduled_run_at(db: AsyncSession):
    stmt = (
        select(BacktestRun.created_at)
        .where(BacktestRun.run_kind == "scheduled_strategy_eval")
        .order_by(BacktestRun.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
