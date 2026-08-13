"""
Rejeu des signaux historiques contre les prix reels ulterieurs pour mesurer
la performance du moteur de score. Voir docs/02 (backtesting) et docs/10
(validation walk-forward, pas de fuite de donnees futures - un signal n'est
jamais compare qu'a des prix strictement posterieurs a son calcul).

Etape 18 : au-dela de precision/win-rate, on ajoute des metriques de qualite
financiere du "rendement de strategie" que l'on obtiendrait en suivant les
signaux (rendement = forward_return dans le sens du signal, negatif s'il va
a l'encontre) - Sharpe, Calmar, profit factor, R:R moyen. Ce sont des
simplifications pedagogiques assumees (pas de taux sans risque, pas
d'annualisation faute de frequence homogene entre signaux) - a lire comme
des indicateurs relatifs pour comparer des runs entre eux, pas des chiffres
"officiels" de performance.
"""
import statistics
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.backtests import repository
from app.domains.backtests.models import BacktestResult
from app.domains.market_data.models import PriceBar
from app.domains.signals.models import Signal
from app.domains.signals.models_ml.baseline_rules import DecisionParams, classify_signal
from app.domains.signals.training import HORIZON_FORWARD_DAYS


@dataclass
class BacktestMetrics:
    precision: float
    win_rate: float
    false_positive_rate: float
    max_drawdown: float
    signal_count: int
    sharpe_ratio: float | None = None
    calmar_ratio: float | None = None
    profit_factor: float | None = None
    avg_risk_reward: float | None = None


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
    strategy_returns: list[float] = []

    for outcome in evaluable:
        bullish_signal = outcome["final_signal"] in ("achat_speculatif", "surveillance")
        is_success = (outcome["forward_return"] > 0) == bullish_signal
        if is_success:
            successes += 1
        else:
            false_positives += 1

        # Rendement "suivi du signal" : positif si le signal avait raison,
        # negatif sinon - c'est la meme convention de sens que le succes/echec
        # ci-dessus, mais garde en valeur continue (pas juste vrai/faux) pour
        # les metriques financieres ci-dessous.
        strategy_return = outcome["forward_return"] if bullish_signal else -outcome["forward_return"]
        strategy_returns.append(strategy_return)

        cumulative *= (1 + outcome["forward_return"]) if bullish_signal else (1 - outcome["forward_return"])
        running_max = max(running_max, cumulative)
        drawdown = (running_max - cumulative) / running_max if running_max > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)

    precision = successes / len(evaluable)
    false_positive_rate = false_positives / len(evaluable)

    sharpe_ratio, calmar_ratio, profit_factor, avg_risk_reward = _compute_financial_metrics(
        strategy_returns, cumulative, max_drawdown
    )

    return BacktestMetrics(
        precision=round(precision, 4),
        win_rate=round(precision, 4),
        false_positive_rate=round(false_positive_rate, 4),
        max_drawdown=round(max_drawdown, 4),
        signal_count=len(signal_outcomes),
        sharpe_ratio=sharpe_ratio,
        calmar_ratio=calmar_ratio,
        profit_factor=profit_factor,
        avg_risk_reward=avg_risk_reward,
    )


def _compute_financial_metrics(
    strategy_returns: list[float], cumulative_return: float, max_drawdown: float
) -> tuple[float | None, float | None, float | None, float | None]:
    """
    Sharpe ratio : rendement moyen par signal / volatilite des rendements par
    signal (taux sans risque suppose nul - simplification assumee). Necessite
    au moins 2 signaux pour calculer un ecart-type.

    Calmar ratio : rendement cumule sur la periode / drawdown max. Version
    simplifiee non annualisee (les signaux n'ont pas de frequence homogene
    d'un actif a l'autre, contrairement a un vrai calcul Calmar sur base
    annuelle).

    Profit factor : somme des gains / somme des pertes (valeur absolue).
    >1 signifie que les gains couvrent les pertes.

    R:R moyen : gain moyen des signaux gagnants / perte moyenne (valeur
    absolue) des signaux perdants.
    """
    if len(strategy_returns) < 2:
        return None, None, None, None

    mean_return = statistics.mean(strategy_returns)
    stdev_return = statistics.stdev(strategy_returns)
    sharpe_ratio = round(mean_return / stdev_return, 4) if stdev_return > 0 else None

    calmar_ratio = round((cumulative_return - 1) / max_drawdown, 4) if max_drawdown > 0 else None

    gains = [r for r in strategy_returns if r > 0]
    losses = [r for r in strategy_returns if r < 0]

    sum_gains = sum(gains)
    sum_losses = abs(sum(losses))
    profit_factor = round(sum_gains / sum_losses, 4) if sum_losses > 0 else None

    avg_win = statistics.mean(gains) if gains else None
    avg_loss = abs(statistics.mean(losses)) if losses else None
    avg_risk_reward = round(avg_win / avg_loss, 4) if avg_win is not None and avg_loss else None

    return sharpe_ratio, calmar_ratio, profit_factor, avg_risk_reward


def _return_price(bar: PriceBar) -> float:
    """
    Etape 19 : le rendement utilise pour le backtesting doit venir du cours
    AJUSTE des dividendes/splits (adjusted_close), sinon un detachement de
    dividende cree une fausse baisse de cours qui pollue precision/Sharpe/
    Calmar (voir docs/06 et le guide de backtesting cite en discussion).
    Repli sur le cours brut si adjusted_close est absent (donnees anciennes,
    avant l'Etape 19).
    """
    return float(bar.adjusted_close) if bar.adjusted_close is not None else float(bar.close)


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
    start_price = _return_price(bars[0])
    end_price = _return_price(bars[-1])
    if start_price == 0:
        return None
    return (end_price - start_price) / start_price


async def run_backtest_for_asset(
    db: AsyncSession,
    asset_id: uuid.UUID,
    horizon: str,
    period_start: date,
    period_end: date,
    decision_params: DecisionParams | None = None,
) -> BacktestMetrics:
    """
    Rejoue les signaux d'un actif/horizon sur une periode donnee : pour
    chaque signal, calcule le rendement reel qui a suivi, puis agrege via
    evaluate_signals(). Les signaux sans assez de prix futurs disponibles
    (trop recents) sont simplement exclus, pas traites comme un echec.

    01/08/2026 (laboratoire de parametres, moteur interne - voir
    kernc_engine.py::SignalReplayStrategy pour le meme principe applique au
    second moteur) : decision_params est optionnel. Omis, comportement
    strictement identique a avant (le final_signal DEJA stocke est utilise
    tel quel). Fourni, chaque signal est RECLASSIFIE a la volee a partir de
    ses 4 scores bruts (technical/news/risk/confidence, inchanges) via
    classify_signal() - permet de tester "et si les seuils/ponderations de
    decision avaient ete autres ?" sur le moteur interne, sans recalculer les
    indicateurs techniques sous-jacents (meme limite assumee que le moteur
    backtesting.py).
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
        if decision_params is not None:
            final_signal = classify_signal(
                float(signal.technical_score),
                float(signal.news_score),
                float(signal.risk_score),
                float(signal.confidence_score),
                params=decision_params,
            )
        else:
            final_signal = signal.final_signal
        outcomes.append({"final_signal": final_signal, "forward_return": forward_return})

    return evaluate_signals(outcomes)


# ---------------------------------------------------------------------------
# Scorecard de fiabilite par strategie (13/08/2026, voir
# jobs/evaluate_strategies_job.py) - agrege UNIQUEMENT les runs automatiques
# hebdomadaires (run_kind="scheduled_strategy_eval", parametres par defaut),
# jamais les tests ad-hoc de l'utilisateur (ParamsLabPanel.vue) dont les
# parametres varient volontairement d'un test a l'autre.
# ---------------------------------------------------------------------------

SCORECARD_WINDOWS = {"90d": 90, "365d": 365, "all": None}


def _aggregate_scheduled_results(results: list[BacktestResult]) -> dict[tuple[str, str], dict]:
    """Regroupe par (strategy_name, horizon) - meme cle que ParamsLabPanel.vue::
    resultKey - et calcule la moyenne du taux de reussite (win_rate, dispo
    pour TOUTES les strategies) et du rendement (Return [%], uniquement pour
    les strategies backtesting.py - absent pour internal_rules, voir
    kernc_engine.py)."""
    groups: dict[tuple[str, str], list[BacktestResult]] = {}
    for r in results:
        key = (r.strategy_name or "inconnu", r.horizon)
        groups.setdefault(key, []).append(r)

    aggregated = {}
    for key, rows in groups.items():
        win_rates = [float(r.win_rate) for r in rows if r.win_rate is not None]
        returns = [
            r.extra_metrics["Return [%]"]
            for r in rows
            if r.extra_metrics and "Return [%]" in r.extra_metrics and r.extra_metrics["Return [%]"] is not None
        ]
        aggregated[key] = {
            "count": len(rows),
            "avg_win_rate": round(sum(win_rates) / len(win_rates), 4) if win_rates else None,
            "avg_return_pct": round(sum(returns) / len(returns), 2) if returns else None,
        }
    return aggregated


async def get_strategy_scorecard(db: AsyncSession) -> dict:
    """
    Pour chaque strategie(+horizon), les stats agregees ci-dessus sur
    chaque fenetre glissante de SCORECARD_WINDOWS - format "liste de lignes"
    (pas un dict imbrique) pour un rendu direct en tableau cote frontend
    (voir schemas.py::StrategyScorecardRow).
    """
    per_window: dict[str, dict[tuple[str, str], dict]] = {}
    for window_key, window_days in SCORECARD_WINDOWS.items():
        since = datetime.now(timezone.utc) - timedelta(days=window_days) if window_days is not None else None
        results = await repository.get_scheduled_results(db, since=since)
        per_window[window_key] = _aggregate_scheduled_results(results)

    all_keys = set()
    for window_stats in per_window.values():
        all_keys.update(window_stats.keys())

    empty_stats = {"count": 0, "avg_win_rate": None, "avg_return_pct": None}
    rows = [
        {
            "strategy_name": strategy_name,
            "horizon": horizon,
            "windows": {wk: per_window[wk].get((strategy_name, horizon), empty_stats) for wk in SCORECARD_WINDOWS},
        }
        for strategy_name, horizon in sorted(all_keys)
    ]

    last_evaluated_at = await repository.get_last_scheduled_run_at(db)
    return {"results": rows, "last_evaluated_at": last_evaluated_at}
