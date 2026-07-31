"""
Bug reel du 30/07/2026 : un cours NaN (yfinance renvoie parfois une bougie
du jour encore en formation avec des OHLC a NaN - float(nan) ne leve aucune
exception) pouvait atteindre price_bars puis empoisonner durablement
avg_cost/cash_balance du portefeuille virtuel (NaN irreversible dans toute
arithmetique ulterieure). Voir docs/STACK.md pour le recit complet.

Ces tests couvrent les deux garde-fous ajoutes (fonctions pures, testables
sans base de donnees ni appel reseau) : le filtre a l'ingestion
(market_data/repository.py:_is_valid_bar) et le garde-fou a l'achat/vente
(portfolio/service.py:_get_latest_price).
"""
import math
from datetime import date
from types import SimpleNamespace

import pytest

from app.core.exceptions import InsufficientDataError
from app.domains.market_data.providers.base import PriceBarDTO
from app.domains.market_data.repository import _is_valid_bar
from app.domains.portfolio.service import _get_latest_price


def _bar(open_=1.0, high=1.0, low=1.0, close=1.0):
    return PriceBarDTO(trade_date=date(2026, 7, 30), open=open_, high=high, low=low, close=close, adjusted_close=close, volume=100)


def test_is_valid_bar_accepts_normal_values():
    assert _is_valid_bar(_bar(close=105.0)) is True


def test_is_valid_bar_rejects_nan_close():
    assert _is_valid_bar(_bar(close=float("nan"))) is False


def test_is_valid_bar_rejects_nan_in_any_ohlc_field():
    assert _is_valid_bar(_bar(open_=float("nan"))) is False
    assert _is_valid_bar(_bar(high=float("nan"))) is False
    assert _is_valid_bar(_bar(low=float("nan"))) is False


class _FakeMarketDataRepository:
    """Double de test minimal - evite de monter une vraie session DB juste
    pour tester la validation du prix (fonction pure de facto une fois le
    bar recupere)."""

    def __init__(self, bar):
        self._bar = bar

    async def get_latest_bar(self, db, asset_id):
        return self._bar


@pytest.mark.asyncio
async def test_get_latest_price_rejects_nan_close(monkeypatch):
    bar = SimpleNamespace(close=float("nan"), trade_date=date(2026, 7, 30))
    monkeypatch.setattr(
        "app.domains.portfolio.service.market_data_repository", _FakeMarketDataRepository(bar)
    )
    with pytest.raises(InsufficientDataError):
        await _get_latest_price(db=None, asset_id=None)


@pytest.mark.asyncio
async def test_get_latest_price_rejects_zero_or_negative_close(monkeypatch):
    bar = SimpleNamespace(close=0.0, trade_date=date(2026, 7, 30))
    monkeypatch.setattr(
        "app.domains.portfolio.service.market_data_repository", _FakeMarketDataRepository(bar)
    )
    with pytest.raises(InsufficientDataError):
        await _get_latest_price(db=None, asset_id=None)


@pytest.mark.asyncio
async def test_get_latest_price_accepts_valid_close(monkeypatch):
    bar = SimpleNamespace(close=105.5, trade_date=date(2026, 7, 30))
    monkeypatch.setattr(
        "app.domains.portfolio.service.market_data_repository", _FakeMarketDataRepository(bar)
    )
    price, trade_date = await _get_latest_price(db=None, asset_id=None)
    assert price == 105.5
    assert trade_date == date(2026, 7, 30)
