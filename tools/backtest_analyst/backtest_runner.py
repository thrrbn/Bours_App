"""
Rejoue un backtest EN LOCAL sur ce PC via backtesting.py, pour recuperer les
transactions individuelles et la courbe de capital en memoire - donnees que
l'application principale NE PERSISTE PAS en base (voir
backend/app/domains/backtests/kernc_engine.py, commentaire explicite :
"_strategy/_equity_curve/_trades qui ne sont pas des scalaires
serialisables en JSON"). C'est exactement pour ca que cet outil rejoue le
backtest lui-meme plutot que d'essayer de lire une donnee qui n'existe nulle
part cote NAS (voir README.md).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import pandas as pd
from backtesting import Backtest

from strategies import STRATEGY_CLASSES

MIN_BARS_REQUIRED = 5  # meme seuil que kernc_engine.py::_load_price_dataframe


class BacktestRunnerError(Exception):
    pass


@dataclass
class LocalBacktestResult:
    strategy_name: str
    stats: dict  # metriques agregees, scalaires uniquement (meme esprit que extra_metrics cote app)
    trades: pd.DataFrame  # une ligne par transaction (EntryTime, ExitTime, PnL, ReturnPct, Duration...)
    equity_curve: pd.DataFrame  # Equity / DrawdownPct par date
    price_df: pd.DataFrame  # OHLCV utilise pour le test (pour recalculer un contexte de prix si besoin)


def _num(value) -> float | None:
    """Meme garde-fous que kernc_engine.py::_num (NaN/Infinity non
    serialisables en JSON) - duplique ici pour la meme raison que
    strategies.py : pas de dependance a l'app principale."""
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "total_seconds"):
        return round(value.total_seconds() / 86400, 2)
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isinf(result) else result


_STATS_KEYS = (
    "# Trades",
    "Win Rate [%]",
    "Return [%]",
    "Buy & Hold Return [%]",
    "Return (Ann.) [%]",
    "Volatility (Ann.) [%]",
    "Max. Drawdown [%]",
    "Avg. Drawdown [%]",
    "Sharpe Ratio",
    "Sortino Ratio",
    "Calmar Ratio",
    "Profit Factor",
    "SQN",
    "Best Trade [%]",
    "Worst Trade [%]",
    "Avg. Trade [%]",
    "Exposure Time [%]",
)


def run_local_backtest(
    price_df: pd.DataFrame,
    strategy_name: str,
    *,
    cash: float = 10_000.0,
    commission: float = 0.001,
    strategy_params: dict | None = None,
) -> LocalBacktestResult:
    if strategy_name not in STRATEGY_CLASSES:
        raise BacktestRunnerError(
            f"Strategie '{strategy_name}' non supportee par cet outil autonome "
            f"(supportees : {', '.join(STRATEGY_CLASSES)}) - voir strategies.py pour pourquoi "
            f"signal_replay/internal_rules sont hors perimetre."
        )
    if len(price_df) < MIN_BARS_REQUIRED:
        raise BacktestRunnerError(
            f"Historique de prix insuffisant ({len(price_df)} bougies, {MIN_BARS_REQUIRED} minimum) "
            f"sur la periode demandee."
        )

    strategy_cls = STRATEGY_CLASSES[strategy_name]
    bt = Backtest(price_df, strategy_cls, cash=cash, commission=commission, exclusive_orders=True, finalize_trades=True)
    stats = bt.run(**(strategy_params or {}))

    scalar_stats = {key: _num(stats[key]) for key in _STATS_KEYS if key in stats}

    trades = stats["_trades"].copy() if "_trades" in stats else pd.DataFrame()
    equity_curve = stats["_equity_curve"].copy() if "_equity_curve" in stats else pd.DataFrame()

    return LocalBacktestResult(
        strategy_name=strategy_name,
        stats=scalar_stats,
        trades=trades,
        equity_curve=equity_curve,
        price_df=price_df,
    )
