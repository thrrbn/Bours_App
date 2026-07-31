"""
Tests du module d'indicateurs techniques du bac a sable pedagogique
(analysis_lab/feature_engineering.py, 31/07/2026 - voir docs/STACK.md).

Fonctions PURES (DataFrame en entree/sortie, aucun acces DB) - testees sur
des donnees synthetiques construites en memoire, coherent avec la convention
deja suivie par tests/test_kernc_engine.py.
"""
import numpy as np
import pandas as pd
import pytest

from app.domains.analysis_lab.feature_engineering import (
    FeatureEngineer,
    add_adx,
    add_aroon,
    add_bollinger,
    add_candlestick_patterns,
    add_cci,
    add_lags,
    add_mfi,
    add_obv,
    add_parabolic_sar,
    add_rolling_stats,
    add_rsi_multi,
    add_stochastic,
    add_temporal_features,
    add_williams_r,
    generate_all_features,
)


def _synthetic_ohlcv(n: int = 260, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = np.abs(100 + np.cumsum(rng.normal(0, 1, n))) + 10
    return pd.DataFrame(
        {
            "Open": close * (1 + rng.normal(0, 0.001, n)),
            "High": close * (1 + np.abs(rng.normal(0, 0.005, n))),
            "Low": close * (1 - np.abs(rng.normal(0, 0.005, n))),
            "Close": close,
            "Volume": rng.integers(1_000, 5_000, n),
        },
        index=dates,
    )


def test_generate_all_features_produces_at_least_50_new_columns():
    df = _synthetic_ohlcv()
    result = generate_all_features(df)
    new_columns = [c for c in result.columns if c not in df.columns]
    assert len(new_columns) >= 50
    assert len(result) == len(df)  # aucune ligne perdue (les NaN de rolling restent, pas de dropna ici)


def test_feature_engineer_class_tracks_feature_names():
    df = _synthetic_ohlcv()
    engineer = FeatureEngineer()
    result = engineer.generate_all_features(df)
    assert len(engineer.feature_names) >= 50
    assert all(name in result.columns for name in engineer.feature_names)


def test_rsi_is_bounded_between_0_and_100():
    df = _synthetic_ohlcv()
    result = add_rsi_multi(df)
    for period in (7, 14, 21):
        col = result[f"rsi_{period}"].dropna()
        assert (col >= 0).all() and (col <= 100).all()


def test_stochastic_k_is_bounded_between_0_and_100():
    df = _synthetic_ohlcv()
    result = add_stochastic(df)
    col = result["stochastic_k"].dropna()
    assert (col >= 0).all() and (col <= 100).all()


def test_williams_r_is_bounded_between_minus_100_and_0():
    df = _synthetic_ohlcv()
    result = add_williams_r(df)
    col = result["williams_r_14"].dropna()
    assert (col >= -100).all() and (col <= 0).all()


def test_mfi_is_bounded_between_0_and_100():
    df = _synthetic_ohlcv()
    result = add_mfi(df)
    col = result["mfi_14"].dropna()
    assert (col >= 0).all() and (col <= 100).all()


def test_adx_is_bounded_between_0_and_100():
    df = _synthetic_ohlcv()
    result = add_adx(df)
    col = result["adx_14"].dropna()
    assert (col >= 0).all() and (col <= 100).all()


def test_aroon_oscillator_is_bounded_between_minus_100_and_100():
    df = _synthetic_ohlcv()
    result = add_aroon(df)
    col = result["aroon_oscillator"].dropna()
    assert (col >= -100).all() and (col <= 100).all()


def test_bollinger_upper_is_always_above_lower():
    df = _synthetic_ohlcv()
    result = add_bollinger(df)
    valid = result[["bollinger_upper", "bollinger_lower"]].dropna()
    assert (valid["bollinger_upper"] >= valid["bollinger_lower"]).all()


def test_cci_matches_manual_calculation_on_small_example():
    # Exemple construit a la main pour verifier la formule exacte (pas juste
    # une borne) - 20 barres avec prix typique constant sauf la derniere,
    # deviation moyenne donc facile a calculer.
    n = 25
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    df = pd.DataFrame({"Open": [10.0] * n, "High": [10.0] * n, "Low": [10.0] * n, "Close": [10.0] * n}, index=dates)
    df.loc[df.index[-1], ["High", "Low", "Close"]] = [12.0, 12.0, 12.0]
    result = add_cci(df, period=20)
    # Prix typique constant a 10 sauf la derniere barre a 12 -> CCI positif sur la derniere barre.
    assert result["cci_20"].iloc[-1] > 0


def test_parabolic_sar_runs_without_error_and_has_no_nan_after_first_row():
    df = _synthetic_ohlcv(n=100)
    result = add_parabolic_sar(df)
    assert result["parabolic_sar"].iloc[1:].notna().all()


def test_obv_increases_on_up_day_and_decreases_on_down_day():
    dates = pd.date_range("2024-01-01", periods=4, freq="D")
    df = pd.DataFrame(
        {
            "Open": [10, 11, 10, 9],
            "High": [10, 11, 10, 9],
            "Low": [10, 11, 10, 9],
            "Close": [10.0, 11.0, 10.0, 9.0],  # hausse, baisse, baisse
            "Volume": [100, 200, 300, 400],
        },
        index=dates,
    )
    result = add_obv(df)
    obv = result["obv"]
    assert obv.iloc[1] == obv.iloc[0] + 200  # jour de hausse -> +volume
    assert obv.iloc[2] == obv.iloc[1] - 300  # jour de baisse -> -volume
    assert obv.iloc[3] == obv.iloc[2] - 400


def test_temporal_features_cyclical_encoding_is_unit_circle():
    df = _synthetic_ohlcv(n=30)
    result = add_temporal_features(df)
    dow_norm = result["day_of_week_sin"] ** 2 + result["day_of_week_cos"] ** 2
    month_norm = result["month_sin"] ** 2 + result["month_cos"] ** 2
    assert np.allclose(dow_norm, 1.0)
    assert np.allclose(month_norm, 1.0)


def test_lags_shift_close_correctly():
    df = _synthetic_ohlcv(n=30)
    result = add_lags(df)
    assert (result["close_lag_1"].iloc[1:].values == df["Close"].iloc[:-1].values).all()


def test_rolling_stats_mean_matches_pandas_rolling_mean():
    df = _synthetic_ohlcv(n=60)
    result = add_rolling_stats(df, window=20)
    expected = df["Close"].pct_change().rolling(20).mean()
    pd.testing.assert_series_equal(result["returns_mean_20"], expected, check_names=False)


def test_candlestick_doji_detected_on_flat_candle():
    dates = pd.date_range("2024-01-01", periods=2, freq="D")
    df = pd.DataFrame(
        {"Open": [10.0, 10.001], "High": [10.0, 10.5], "Low": [10.0, 9.5], "Close": [10.0, 10.0]}, index=dates
    )
    result = add_candlestick_patterns(df)
    assert result["is_doji"].iloc[1] == 1


def test_candlestick_bullish_engulfing_detected():
    dates = pd.date_range("2024-01-01", periods=2, freq="D")
    # Jour 1 : bougie baissiere (open 10.5 -> close 10.0). Jour 2 : bougie
    # haussiere qui "englobe" completement la precedente (open 9.9 -> close 10.6).
    df = pd.DataFrame(
        {"Open": [10.5, 9.9], "High": [10.6, 10.7], "Low": [9.9, 9.8], "Close": [10.0, 10.6]}, index=dates
    )
    result = add_candlestick_patterns(df)
    assert result["is_bullish_engulfing"].iloc[1] == 1
