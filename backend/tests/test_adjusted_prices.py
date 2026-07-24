"""
Tests Etape 19 : les calculs de rendement (backtesting, tendance historique)
doivent preferer le cours ajuste des dividendes/splits (adjusted_close) au
cours brut, pour eviter qu'un detachement de dividende ne simule une fausse
baisse. Fonctions pures, testees avec de simples objets factices (duck
typing sur .close / .adjusted_close, comme PriceBar).
"""
from types import SimpleNamespace

from app.domains.backtests.service import _return_price
from app.domains.market_data.service import _adjusted_or_close


def _bar(close: float, adjusted_close: float | None):
    return SimpleNamespace(close=close, adjusted_close=adjusted_close)


def test_return_price_prefers_adjusted_close_when_present():
    bar = _bar(close=100.0, adjusted_close=97.5)  # ex-dividende : close brut a chute
    assert _return_price(bar) == 97.5


def test_return_price_falls_back_to_close_when_adjusted_close_missing():
    bar = _bar(close=42.0, adjusted_close=None)  # donnees anciennes, avant Etape 19
    assert _return_price(bar) == 42.0


def test_adjusted_or_close_prefers_adjusted_close_when_present():
    bar = _bar(close=50.0, adjusted_close=48.0)
    assert _adjusted_or_close(bar) == 48.0


def test_adjusted_or_close_falls_back_to_close_when_adjusted_close_missing():
    bar = _bar(close=15.0, adjusted_close=None)
    assert _adjusted_or_close(bar) == 15.0
