"""Tests des indicateurs techniques (docs/10) - fonction pure sur DataFrame pandas."""
import numpy as np
import pandas as pd

from app.domains.market_data.service import compute_indicators_dataframe


def _make_price_series(prices: list[float]) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=len(prices), freq="D")
    return pd.DataFrame({"close": prices}, index=dates)


def test_sma_20_is_nan_before_enough_history():
    df = _make_price_series([100.0] * 10)
    result = compute_indicators_dataframe(df)
    assert result["sma_20"].isna().all()


def test_sma_20_matches_manual_average_once_enough_history():
    prices = [100.0] * 19 + [120.0]
    df = _make_price_series(prices)
    result = compute_indicators_dataframe(df)
    expected = (sum(prices[-20:])) / 20
    assert np.isclose(result["sma_20"].iloc[-1], expected)


def test_rsi_is_high_for_strictly_increasing_prices():
    prices = [100 + i for i in range(30)]
    df = _make_price_series(prices)
    result = compute_indicators_dataframe(df)
    assert result["rsi_14"].iloc[-1] > 70


def test_volatility_is_zero_for_constant_prices():
    df = _make_price_series([100.0] * 30)
    result = compute_indicators_dataframe(df)
    assert result["volatility_20d"].iloc[-1] == 0.0
