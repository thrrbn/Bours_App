"""
Tests du provider Binance (donnees de marche publiques, voir docs/17) :
parse_klines est une fonction pure isolee de l'appel reseau (meme principe
que compute_indicators_dataframe) - testable sans mock HTTP.
"""
from datetime import date

from app.domains.market_data.providers.binance import parse_klines
from app.domains.market_data.service import provider_for_market


def _kline(open_time_ms: int, o: str, h: str, l: str, c: str, v: str) -> list:
    # Format positionnel Binance : les 6 derniers champs (closeTime,
    # quoteVolume, trades, takerBuyBase, takerBuyQuote, ignore) sont
    # ininfluents pour parse_klines - valeurs bidon ici.
    return [open_time_ms, o, h, l, c, v, open_time_ms + 86_399_999, "0", 0, "0", "0", "0"]


def test_parse_klines_maps_ohlcv_fields():
    raw = [_kline(1_700_000_000_000, "35000.10", "35500.00", "34800.00", "35200.50", "1234.56789")]
    bars = parse_klines(raw)

    assert len(bars) == 1
    bar = bars[0]
    assert bar.trade_date == date(2023, 11, 14)
    assert bar.open == 35000.10
    assert bar.high == 35500.00
    assert bar.low == 34800.00
    assert bar.close == 35200.50
    assert bar.volume == 1234  # troncature entiere du volume (comme Yahoo Finance)


def test_parse_klines_adjusted_close_equals_close_no_corporate_actions():
    """Pas de dividendes/splits en crypto : contrairement a Yahoo Finance,
    adjusted_close doit toujours valoir close (voir docs/STACK.md, Etape 19)."""
    raw = [_kline(1_700_000_000_000, "100", "110", "90", "105", "10")]
    bar = parse_klines(raw)[0]
    assert bar.adjusted_close == bar.close == 105.0


def test_parse_klines_handles_multiple_entries_in_order():
    raw = [
        _kline(1_700_000_000_000, "100", "110", "90", "105", "10"),
        _kline(1_700_086_400_000, "105", "120", "104", "118", "20"),
    ]
    bars = parse_klines(raw)
    assert [b.trade_date for b in bars] == [date(2023, 11, 14), date(2023, 11, 15)]


def test_parse_klines_empty_list_returns_empty():
    assert parse_klines([]) == []


def test_provider_for_market_routes_binance_assets_to_binance_source():
    provider, source = provider_for_market("BINANCE")
    assert source == "binance"
    assert type(provider).__name__ == "BinanceProvider"


def test_provider_for_market_defaults_to_yahoo_finance_for_stocks():
    provider, source = provider_for_market("EURONEXT_BRUSSELS")
    assert source == "yahoo_finance"
    assert type(provider).__name__ == "YahooFinanceProvider"
