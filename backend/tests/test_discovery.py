"""
Tests de la decouverte de candidats (assets/discovery.py) : parse_screener_quotes
est une fonction pure isolee de l'appel reseau (meme principe que
binance.parse_klines) - testable sans mock du screener yfinance.
"""
from app.domains.assets.discovery import guess_market, parse_screener_quotes


def test_parse_screener_quotes_extracts_symbol_name_market():
    payload = {
        "quotes": [
            {"symbol": "AAPL", "shortName": "Apple Inc.", "exchange": "NMS"},
            {"symbol": "V", "shortName": "Visa Inc.", "exchange": "NYQ"},
        ]
    }
    result = parse_screener_quotes(payload)
    assert result == [
        {"symbol": "AAPL", "name": "Apple Inc.", "market_guess": "NASDAQ"},
        {"symbol": "V", "name": "Visa Inc.", "market_guess": "NYSE"},
    ]


def test_parse_screener_quotes_skips_entries_without_symbol():
    payload = {"quotes": [{"shortName": "No Symbol"}, {"symbol": "AAPL", "shortName": "Apple Inc."}]}
    result = parse_screener_quotes(payload)
    assert len(result) == 1
    assert result[0]["symbol"] == "AAPL"


def test_parse_screener_quotes_falls_back_to_symbol_when_name_missing():
    payload = {"quotes": [{"symbol": "XYZ", "exchange": "NMS"}]}
    assert parse_screener_quotes(payload)[0]["name"] == "XYZ"


def test_parse_screener_quotes_handles_missing_or_empty_quotes():
    assert parse_screener_quotes({}) == []
    assert parse_screener_quotes({"quotes": []}) == []
    assert parse_screener_quotes({"quotes": None}) == []


def test_guess_market_uses_exchange_code_first():
    assert guess_market({"exchange": "NMS"}) == "NASDAQ"
    assert guess_market({"exchange": "NYQ"}) == "NYSE"


def test_guess_market_falls_back_to_full_exchange_name():
    assert guess_market({"exchange": "", "fullExchangeName": "NasdaqGS"}) == "NASDAQ"
    assert guess_market({"exchange": "", "fullExchangeName": "NYSE"}) == "NYSE"


def test_guess_market_defaults_to_us_autre_when_unknown():
    assert guess_market({"exchange": "TYO", "fullExchangeName": "Tokyo"}) == "US_AUTRE"
    assert guess_market({}) == "US_AUTRE"
