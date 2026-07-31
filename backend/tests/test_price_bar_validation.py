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

Suite du 31/07/2026 (voir docs/STACK.md) : filtrer le NaN a l'ingestion
n'empeche pas une ligne DEJA corrompue AVANT le correctif de rester "la plus
recente par date" indefiniment (un rafraichissement ulterieur ne la remplace
que si Yahoo Finance renvoie entre-temps une valeur non-NaN pour CETTE MEME
date). Corrige a la source dans get_latest_bar() (filtre SQL). Le test
ci-dessous verifie la requete compilee plutot que d'executer contre une vraie
base (convention du projet : pas de DB reelle dans les tests), mais confirme
que Decimal('NaN') est bien utilise (piege Postgres : NaN = NaN est VRAI pour
NUMERIC, contrairement a IEEE754 - `close != close` ne fonctionnerait pas).
"""
import math
import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from app.core.exceptions import InsufficientDataError
from app.domains.market_data.providers.base import PriceBarDTO
from app.domains.market_data.repository import _is_valid_bar, get_latest_bar
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


class _CapturingSession:
    """Double minimal qui capture le SELECT construit par get_latest_bar()
    sans se connecter a une vraie base - on verifie la requete COMPILEE plutot
    que son execution (convention du projet, voir docstring en tete de fichier)."""

    def __init__(self):
        self.captured_stmt = None

    async def execute(self, stmt):
        self.captured_stmt = stmt

        class _Result:
            def scalar_one_or_none(self_inner):
                return None

        return _Result()


@pytest.mark.asyncio
async def test_get_latest_bar_query_excludes_nan_and_non_positive_close():
    session = _CapturingSession()
    await get_latest_bar(session, uuid.uuid4())

    compiled = str(session.captured_stmt.compile(compile_kwargs={"literal_binds": True}))
    # Piege Postgres (voir docstring de get_latest_bar) : NaN = NaN est VRAI
    # pour NUMERIC, donc on doit comparer explicitement a la valeur Decimal
    # NaN plutot qu'a un `close != close` qui ne filtrerait rien.
    assert "NaN" in compiled
    assert "price_bars.close > 0" in compiled or "price_bars.close > 0.0" in compiled
