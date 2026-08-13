"""
Job hebdomadaire (13/08/2026, demande explicite de l'utilisateur : "pouvoir
evaluer les strategies testees dans le temps") - rejoue les 7 strategies de
backtest (internal_rules, signal_replay, sma_cross, rsi_mean_reversion,
macd_cross, bollinger_reversion, buy_and_hold) sur chaque position du
portefeuille virtuel, avec des parametres PAR DEFAUT uniquement (jamais ceux
d'un utilisateur - voir kernc_engine.py) et sur une fenetre glissante fixe
(365 derniers jours), pour alimenter un scorecard de fiabilite par strategie
qui evolue dans le temps.

Complementaire de deux fonctionnalites deja existantes :
- ParamsLabPanel.vue / POST /run-kernc /run : backtest A LA DEMANDE, avec des
  parametres CHOISIS par l'utilisateur, sur UN actif a la fois - jamais
  suivi automatiquement dans la duree.
- signal_reliability (domaine separe) : evalue les signaux REELS deja
  produits en production, pas les strategies de backtest.

Reutilise les positions du portefeuille virtuel comme jeu de test (meme
convention que analysis_lab/service.py::compare_portfolio, deja demandee
explicitement par l'utilisateur pour une autre fonctionnalite : "reprendre
des indices du portefeuille pour verifier par rapport a notre calcul
reelle").

run_kind="scheduled_strategy_eval" (voir backtests/models.py) permet au
scorecard d'agreger UNIQUEMENT ces runs a parametres fixes, jamais les runs
ad-hoc de l'utilisateur (qui testent volontairement des reglages differents
d'un test a l'autre - les melanger fausserait completement la tendance).
"""
import logging
from datetime import date, timedelta

from app.database import AsyncSessionLocal
from app.domains.backtests import kernc_engine, repository, service
from app.domains.portfolio import repository as portfolio_repository

logger = logging.getLogger(__name__)

RUN_KIND = "scheduled_strategy_eval"
LOOKBACK_DAYS = 365
HORIZONS = ("short", "medium", "long")


async def evaluate_strategies_job() -> dict:
    async with AsyncSessionLocal() as db:
        positions = await portfolio_repository.list_positions(db)
        period_end = date.today()
        period_start = period_end - timedelta(days=LOOKBACK_DAYS)

        run = await repository.create_run(
            db,
            engine_version=f"scheduled-{period_end.isoformat()}",
            period_start=period_start,
            period_end=period_end,
            asset_scope={"asset_ids": [str(p.asset_id) for p in positions]},
            run_kind=RUN_KIND,
        )

        saved_count = 0
        errors = 0

        for position in positions:
            asset_id = position.asset_id
            try:
                # 1) Moteur interne (parametres par defaut = final_signal deja
                # stocke en production, AUCUNE reclassification).
                for horizon in HORIZONS:
                    metrics = await service.run_backtest_for_asset(db, asset_id, horizon, period_start, period_end)
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
                    saved_count += 1

                # 2) Strategies backtesting.py (parametres par defaut de chaque
                # classe - voir kernc_engine.py - jamais d'override).
                # generate_plot=False : inutile pour un run automatique jamais
                # affiche, evite des dizaines de generations Bokeh par semaine.
                for strategy_name in kernc_engine.ALL_STRATEGIES:
                    strategy_horizons = HORIZONS if strategy_name == kernc_engine.STRATEGY_SIGNAL_REPLAY else ("n/a",)
                    for horizon in strategy_horizons:
                        result = await kernc_engine.run_kernc_backtest(
                            db,
                            asset_id,
                            strategy_name,
                            period_start,
                            period_end,
                            horizon=horizon if horizon != "n/a" else "medium",
                            generate_plot=False,
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
                        saved_count += 1
            except Exception:
                errors += 1
                logger.exception("Echec evaluation strategies pour l'actif %s", asset_id)

        logger.info(
            "evaluate_strategies_job termine: run_id=%s, %s positions, %s resultats sauvegardes, %s erreurs",
            run.id,
            len(positions),
            saved_count,
            errors,
        )
        return {"run_id": str(run.id), "positions": len(positions), "results_saved": saved_count, "errors": errors}
