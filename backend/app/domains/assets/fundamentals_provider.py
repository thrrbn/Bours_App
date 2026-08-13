"""
Fondamentaux d'un titre (secteur, capitalisation, PER, rendement du
dividende, fourchette 52 semaines, beta, resume d'activite) via yfinance
(Ticker.info) - memes reserves que market_data/providers/yahoo_finance.py et
analyst/provider.py : endpoint non contractuel, champs frequemment absents
(surtout sur les valeurs europeennes de taille moyenne, voir docs/17). Aucun
champ n'est requis individuellement - un ticker valide mais peu couvert
renvoie un DTO partiellement rempli plutot qu'une erreur.

Point de vigilance dividend_yield : les versions recentes de yfinance
renvoient deja un pourcentage (ex. 3.25 pour 3.25%), pas une fraction
(0.0325). Stocke tel quel ici, affiche avec un "%" cote frontend sans
transformation supplementaire - a revalider si le comportement de yfinance
change (voir docs/17-limites-legales-techniques.md).
"""
import yfinance as yf

from app.core.exceptions import DataProviderError
from app.domains.assets.discovery import guess_market


class FundamentalsDTO:
    def __init__(
        self,
        name: str | None,
        sector: str | None,
        industry: str | None,
        currency: str | None,
        market_cap: int | None,
        trailing_pe: float | None,
        forward_pe: float | None,
        dividend_yield: float | None,
        week52_low: float | None,
        week52_high: float | None,
        beta: float | None,
        return_on_equity: float | None,
        debt_to_equity: float | None,
        profit_margin: float | None,
        price_to_book: float | None,
        ev_to_ebitda: float | None,
        business_summary: str | None,
        last_price: float | None,
        market_guess: str,
    ):
        self.name = name
        self.sector = sector
        self.industry = industry
        self.currency = currency
        self.market_cap = market_cap
        self.trailing_pe = trailing_pe
        self.forward_pe = forward_pe
        self.dividend_yield = dividend_yield
        self.week52_low = week52_low
        self.week52_high = week52_high
        self.beta = beta
        self.return_on_equity = return_on_equity
        self.debt_to_equity = debt_to_equity
        self.profit_margin = profit_margin
        self.price_to_book = price_to_book
        self.ev_to_ebitda = ev_to_ebitda
        self.business_summary = business_summary
        self.last_price = last_price
        self.market_guess = market_guess


def _safe_float(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def fetch_fundamentals(ticker: str) -> FundamentalsDTO:
    """Appel bloquant (meme convention que yahoo_finance.py/analyst/provider.py
    - pas d'executor dedie). Leve DataProviderError si Yahoo ne connait pas du
    tout ce ticker (dict d'info quasi vide, cas frequent pour un symbole mal
    forme plutot qu'une exception franche cote yfinance)."""
    try:
        info = yf.Ticker(ticker).info
    except Exception as exc:  # yfinance ne documente pas un type d'exception stable
        raise DataProviderError(f"Echec de recuperation des fondamentaux Yahoo Finance pour {ticker}: {exc}") from exc

    if not info or not (info.get("shortName") or info.get("longName") or info.get("regularMarketPrice")):
        raise DataProviderError(f"Ticker introuvable sur Yahoo Finance: {ticker}")

    return FundamentalsDTO(
        name=info.get("shortName") or info.get("longName"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        currency=info.get("currency"),
        market_cap=_safe_int(info.get("marketCap")),
        trailing_pe=_safe_float(info.get("trailingPE")),
        forward_pe=_safe_float(info.get("forwardPE")),
        dividend_yield=_safe_float(info.get("dividendYield")),
        week52_low=_safe_float(info.get("fiftyTwoWeekLow")),
        week52_high=_safe_float(info.get("fiftyTwoWeekHigh")),
        beta=_safe_float(info.get("beta")),
        # 13/08/2026 : returnOnEquity/profitMargins renvoyes par yfinance en
        # FRACTION (0.15 = 15%, meme convention que la plupart des champs
        # "Margins"/"Return" de l'API Yahoo, a la difference de dividendYield
        # deja en % - voir point de vigilance en tete de fichier). Affiche
        # avec x100 cote frontend. debtToEquity/priceToBook/enterpriseToEbitda
        # sont deja des ratios simples (pas de transformation).
        return_on_equity=_safe_float(info.get("returnOnEquity")),
        debt_to_equity=_safe_float(info.get("debtToEquity")),
        profit_margin=_safe_float(info.get("profitMargins")),
        price_to_book=_safe_float(info.get("priceToBook")),
        ev_to_ebitda=_safe_float(info.get("enterpriseToEbitda")),
        business_summary=info.get("longBusinessSummary"),
        last_price=_safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
        market_guess=guess_market(info, ticker=ticker),
    )
