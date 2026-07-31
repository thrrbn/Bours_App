"""
Tests des couts complementaires ajoutes au portefeuille virtuel le 31/07/2026
(voir docs/STACK.md) suite au constat que le rendement simule ne tenait pas
compte des dividendes ni de la taxe belge sur les operations de bourse (TOB) :
- portfolio/service.py::_tob_amount (fonction pure)
- jobs/credit_dividends_job.py::_net_dividend_amount (fonction pure)
- portfolio/repository.py::get_total_fees (requete compilee, meme convention
  que test_price_bar_validation.py::test_get_latest_bar_query_excludes_nan_and_non_positive_close -
  pas de DB reelle dans les tests, voir tests/conftest.py).
"""
from types import SimpleNamespace

import pytest

from app.domains.portfolio.repository import get_total_fees
from app.domains.portfolio.service import _tob_amount
from app.jobs.credit_dividends_job import _net_dividend_amount


def _settings(tob_pct=0.0035):
    return SimpleNamespace(portfolio_tob_pct=tob_pct)


def test_tob_amount_is_zero_for_binance_assets():
    asset = SimpleNamespace(market="BINANCE")
    assert _tob_amount(asset, execution_price=100.0, quantity=10, settings=_settings()) == 0.0


def test_tob_amount_applies_configured_rate_for_stocks():
    asset = SimpleNamespace(market="EURONEXT_BRUSSELS")
    # 100 EUR/action * 10 actions * 0.35% = 3.5 EUR
    assert _tob_amount(asset, execution_price=100.0, quantity=10, settings=_settings()) == 3.5


def test_tob_amount_scales_with_a_different_configured_rate():
    asset = SimpleNamespace(market="NASDAQ")
    # 200 EUR/action * 5 actions * 1% = 10 EUR
    assert _tob_amount(asset, execution_price=200.0, quantity=5, settings=_settings(tob_pct=0.01)) == 10.0


def test_net_dividend_amount_applies_withholding_tax():
    # 10 actions * 2 EUR/action = 20 EUR brut, moins 30% de precompte -> 14 EUR net
    assert _net_dividend_amount(quantity_held=10, amount_per_share=2.0, withholding_pct=0.30) == 14.0


def test_net_dividend_amount_with_zero_withholding_returns_gross():
    assert _net_dividend_amount(quantity_held=5, amount_per_share=1.5, withholding_pct=0.0) == 7.5


def test_net_dividend_amount_rounds_to_cents():
    result = _net_dividend_amount(quantity_held=3, amount_per_share=0.333, withholding_pct=0.30)
    assert result == round(3 * 0.333 * 0.70, 2)


class _CapturingSession:
    """Meme double minimal que test_price_bar_validation.py - capture la
    requete SQL compilee sans se connecter a une vraie base."""

    def __init__(self):
        self.captured_stmt = None

    async def execute(self, stmt):
        self.captured_stmt = stmt

        class _Result:
            def scalar_one(self_inner):
                return 0

        return _Result()


@pytest.mark.asyncio
async def test_get_total_fees_query_includes_commission_and_tob():
    session = _CapturingSession()
    await get_total_fees(session)

    compiled = str(session.captured_stmt.compile(compile_kwargs={"literal_binds": True}))
    # 31/07/2026 : la TOB doit etre incluse dans le total des frais, comme la
    # commission - contrairement au slippage (cout de marche, deja compte a
    # part dans le prix execute, pas un "frais" preleve).
    assert "commission" in compiled
    assert "tob_amount" in compiled
