"""
Tests du second moteur de backtest (backtesting.py, integre le 31/07/2026 -
voir app/domains/backtests/kernc_engine.py et docs/STACK.md pour le recit).

On teste ici uniquement ce qui est isolable sans base de donnees ni reseau :
- _num() / _stats_to_extra_metrics() : conversion pure de la Stats retournee
  par Backtest.run() vers un dict JSON-serialisable.
- Les strategies elles-memes (SignalReplayStrategy, SmaCrossStrategy,
  BuyAndHoldStrategy), executees par un vrai Backtest sur un DataFrame
  synthetique construit en memoire (aucun appel a _load_price_dataframe /
  _load_signal_scores, qui necessitent une session DB async - non couverts
  ici, coherent avec la convention deja suivie par test_price_bar_validation.py).

31/07/2026 : "laboratoire de parametres" (voir docs/STACK.md) - SignalReplayStrategy
ne consomme plus un code de signal deja fige (`signal_map`) mais des scores
bruts (`signal_scores`) reclassifies a la volee via classify_signal(), et
SmaCrossStrategy accepte n1/n2 en override via bt.run(). Tests couvrant ces
deux leviers ajoutes en fin de fichier.
"""
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from backtesting import Backtest

from app.domains.backtests.kernc_engine import (
    BuyAndHoldStrategy,
    SignalReplayStrategy,
    SmaCrossStrategy,
    _num,
    _stats_to_extra_metrics,
)
from app.domains.signals.models_ml.baseline_rules import DecisionParams


def _synthetic_ohlcv(n: int = 120, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = np.abs(100 + np.cumsum(rng.normal(0, 1, n))) + 10
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": rng.integers(1_000, 5_000, n),
        },
        index=dates,
    )


def test_num_returns_none_for_missing_key():
    stats = pd.Series({"Sharpe Ratio": 1.23})
    assert _num(stats, "Nonexistent") is None


def test_num_returns_none_for_nan():
    stats = pd.Series({"Sharpe Ratio": float("nan")})
    assert _num(stats, "Sharpe Ratio") is None


def test_num_converts_timedelta_to_days():
    stats = pd.Series({"Max. Drawdown Duration": pd.Timedelta(days=10, hours=12)})
    assert _num(stats, "Max. Drawdown Duration") == pytest.approx(10.5)


def test_num_converts_plain_scalar():
    stats = pd.Series({"Sharpe Ratio": 1.5})
    assert _num(stats, "Sharpe Ratio") == 1.5


def test_stats_to_extra_metrics_excludes_non_serializable_objects():
    df = _synthetic_ohlcv()
    bt = Backtest(df, BuyAndHoldStrategy, cash=10_000, commission=0.001, finalize_trades=True)
    stats = bt.run()
    extra = _stats_to_extra_metrics(stats)
    # Ces cles ne doivent JAMAIS apparaitre (objets non serialisables en JSON).
    assert "_strategy" not in extra
    assert "_equity_curve" not in extra
    assert "_trades" not in extra
    # Toutes les valeurs conservees doivent etre des scalaires simples.
    assert all(isinstance(v, (int, float)) for v in extra.values())


def test_buy_and_hold_strategy_buys_once_and_holds():
    df = _synthetic_ohlcv()
    # finalize_trades=True : cloture la position encore ouverte a la fin du
    # backtest pour qu'elle soit comptee dans "# Trades" - sans ca,
    # backtesting.py exclut les trades encore ouverts des stats (avertissement
    # "Some trades remain open"), ce qui est le cas normal pour du buy&hold
    # pur (on ne revend jamais avant la fin de la periode).
    bt = Backtest(df, BuyAndHoldStrategy, cash=10_000, commission=0.0, finalize_trades=True)
    stats = bt.run()
    assert stats["# Trades"] == 1
    assert stats["Exposure Time [%]"] > 90  # investi quasiment tout le temps


def test_sma_cross_strategy_runs_without_error_on_synthetic_data():
    df = _synthetic_ohlcv(n=250)
    bt = Backtest(df, SmaCrossStrategy, cash=10_000, commission=0.001, exclusive_orders=True)
    stats = bt.run()
    # Pas d'assertion forte sur le rendement (donnees aleatoires) - on verifie
    # juste que la strategie produit une simulation coherente (pas d'exception,
    # nombre de trades non negatif).
    assert stats["# Trades"] >= 0


# Scores bruts (technical, news, risk, confidence) qui, avec
# DEFAULT_DECISION_PARAMS, classifient respectivement en achat_speculatif et
# vente_defensive (voir test_classify_signal_with_defaults_matches_historical_thresholds
# dans test_signals_engine.py pour la meme verification cote moteur de signal).
_BULLISH_SCORES = (80.0, 60.0, 40.0, 80.0)
_BEARISH_SCORES = (20.0, 20.0, 65.0, 80.0)


def test_signal_replay_strategy_buys_on_bullish_and_sells_on_bearish():
    df = _synthetic_ohlcv(n=60)
    start_date = df.index[0].date()
    buy_date = start_date + timedelta(days=10)
    sell_date = start_date + timedelta(days=30)
    signal_scores = {buy_date: _BULLISH_SCORES, sell_date: _BEARISH_SCORES}

    bt = Backtest(df, SignalReplayStrategy, cash=10_000, commission=0.0, exclusive_orders=True)
    stats = bt.run(signal_scores=signal_scores)

    assert stats["# Trades"] == 1  # un achat suivi d'une vente = un trade ferme


def test_signal_replay_strategy_ignores_neutral_and_stays_flat():
    df = _synthetic_ohlcv(n=30)
    signal_scores: dict = {}  # aucun signal connu -> reste 'neutre' -> jamais achete
    bt = Backtest(df, SignalReplayStrategy, cash=10_000, commission=0.0)
    stats = bt.run(signal_scores=signal_scores)
    assert stats["# Trades"] == 0


def test_signal_replay_strategy_with_default_decision_params_matches_no_override():
    df = _synthetic_ohlcv(n=60)
    start_date = df.index[0].date()
    buy_date = start_date + timedelta(days=10)
    signal_scores = {buy_date: _BULLISH_SCORES}

    bt = Backtest(df, SignalReplayStrategy, cash=10_000, commission=0.0, finalize_trades=True)
    stats_no_override = bt.run(signal_scores=signal_scores)
    stats_explicit_default = bt.run(signal_scores=signal_scores, decision_params=DecisionParams())

    assert stats_no_override["# Trades"] == stats_explicit_default["# Trades"] == 1


def test_signal_replay_strategy_custom_decision_params_changes_outcome():
    df = _synthetic_ohlcv(n=60)
    start_date = df.index[0].date()
    # Combined = 0.5*60 + 0.5*40 = 50 -> ni bullish ni bearish avec les seuils
    # par defaut (45 < 50 < 55 -> "neutre", voir classify_signal) : aucun
    # trade. Avec un seuil d'achat abaisse a 45, ce meme combined (50) et un
    # risque bas (30 < 50) declenchent achat_speculatif.
    borderline_scores = {start_date + timedelta(days=5): (60.0, 40.0, 30.0, 80.0)}

    bt = Backtest(df, SignalReplayStrategy, cash=10_000, commission=0.0, finalize_trades=True)
    stats_default = bt.run(signal_scores=borderline_scores)
    stats_lenient = bt.run(signal_scores=borderline_scores, decision_params=DecisionParams(buy_threshold=45.0))

    assert stats_default["# Trades"] == 0
    assert stats_lenient["# Trades"] == 1


def test_sma_cross_strategy_accepts_n1_n2_override():
    df = _synthetic_ohlcv(n=250)
    bt = Backtest(df, SmaCrossStrategy, cash=10_000, commission=0.001, exclusive_orders=True, finalize_trades=True)
    stats_default = bt.run()
    stats_override = bt.run(n1=5, n2=15)
    # Verifie que l'override a bien ete applique a l'instance de strategie
    # (plutot que d'inferer indirectement depuis le nombre de trades, peu
    # fiable sur des donnees aleatoires).
    assert stats_default["_strategy"].n1 == 10 and stats_default["_strategy"].n2 == 20
    assert stats_override["_strategy"].n1 == 5 and stats_override["_strategy"].n2 == 15
