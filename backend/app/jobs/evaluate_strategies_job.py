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

Profils de decision (14/08/2026, demande explicite : "en fonction des
resultats de fiabilite obtenus dans le temps, proposer les parametres les
plus adaptes et le comparer au backtesting") - DECISION_PROFILES ci-dessous
ajoute 2 variantes fixes (prudent/agressif) en plus du profil par defaut deja
suivi, pour internal_rules et signal_replay UNIQUEMENT (les seules strategies
pilotees par DecisionParams - SMA/RSI/MACD/Bollinger/buy&hold ont leurs
propres leviers, non concernes). Chaque profil est reevalue CHAQUE SEMAINE
sur la meme fenetre glissante que le profil par defaut, avec les donnees les
plus recentes a chaque run - c'est ce suivi repete dans le temps, pas une
recherche optimisee une seule fois sur des donnees deja connues, qui permet
de recommander un profil sans risque de surapprentissage (contrairement a
une grille testee une fois sur toute la periode). Chaque profil apparait
comme une ligne distincte du scorecard (strategy_name suffixe "::profil",
voir _profile_strategy_name) - le classement par taux de reussite deja
existant dans SignalReliabilityView.vue sert directement de comparaison.
"""
import logging
from datetime import date, timedelta

from app.database import AsyncSessionLocal
from app.domains.backtests import kernc_engine, repository, service
from app.domains.portfolio import repository as portfolio_repository
from app.domains.signals.models_ml.baseline_rules import DecisionParams

logger = logging.getLogger(__name__)

RUN_KIND = "scheduled_strategy_eval"
LOOKBACK_DAYS = 365
HORIZONS = ("short", "medium", "long")

# "" (defaut) reutilise le final_signal deja stocke / DEFAULT_DECISION_PARAMS,
# comportement de production strictement inchange pour ce profil. Les deux
# variantes deplacent les seuils/tolerances symetriquement par rapport au
# profil par defaut (buy_threshold=70, buy_max_risk=50, min_confidence=30) :
# "prudent" exige plus de certitude et de marge avant d'agir (achete plus
# tard, vend plus tot), "agressif" l'inverse (achete plus tot, reste investi
# plus longtemps). L'ordre des seuils (buy > watch > caution > sell) est
# preserve dans les deux cas - voir DecisionParams pour la signification de
# chaque champ.
DECISION_PROFILES: dict[str, DecisionParams | None] = {
    "": None,
    "prudent": DecisionParams(
        technical_weight=0.5,
        news_weight=0.5,
        buy_threshold=75.0,
        watch_threshold=60.0,
        caution_threshold=45.0,
        sell_threshold=35.0,
        buy_max_risk=40.0,
        sell_min_risk=50.0,
        min_confidence=40.0,
    ),
    "agressif": DecisionParams(
        technical_weight=0.5,
        news_weight=0.5,
        buy_threshold=62.0,
        watch_threshold=50.0,
        caution_threshold=40.0,
        sell_threshold=25.0,
        buy_max_risk=65.0,
        sell_min_risk=70.0,
        min_confidence=20.0,
    ),
}


def _profile_strategy_name(base: str, profile_name: str) -> str:
    return f"{base}::{profile_name}" if profile_name else base


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
                # 1) Moteur interne : profil par defaut (final_signal deja
                # stocke en production, AUCUNE reclassification) + profils
                # prudent/agressif (reclassifies via decision_params, voir
                # DECISION_PROFILES en tete de module).
                for profile_name, profile_params in DECISION_PROFILES.items():
                    for horizon in HORIZONS:
                        metrics = await service.run_backtest_for_asset(
                            db, asset_id, horizon, period_start, period_end, decision_params=profile_params
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
                            strategy_name=_profile_strategy_name("internal_rules", profile_name),
                        )
                        saved_count += 1

                # 2) Strategies backtesting.py (parametres par defaut de chaque
                # classe - voir kernc_engine.py - jamais d'override), sauf
                # signal_replay qui suit les 3 memes profils de decision que
                # le moteur interne ci-dessus (seule strategie backtesting.py
                # pilotee par decision_params). generate_plot=False : inutile
                # pour un run automatique jamais affiche, evite des dizaines
                # de generations Bokeh par semaine.
                for strategy_name in kernc_engine.ALL_STRATEGIES:
                    if strategy_name == kernc_engine.STRATEGY_SIGNAL_REPLAY:
                        profiles = DECISION_PROFILES
                        strategy_horizons = HORIZONS
                    else:
                        profiles = {"": None}
                        strategy_horizons = ("n/a",)
                    for profile_name, profile_params in profiles.items():
                        for horizon in strategy_horizons:
                            result = await kernc_engine.run_kernc_backtest(
                                db,
                                asset_id,
                                strategy_name,
                                period_start,
                                period_end,
                                horizon=horizon if horizon != "n/a" else "medium",
                                decision_params=profile_params,
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
                                strategy_name=_profile_strategy_name(result["strategy_name"], profile_name),
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
