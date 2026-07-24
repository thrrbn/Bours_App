"""
Implementation Yahoo Finance du MarketDataProvider.

Attention : Yahoo Finance n'expose pas d'API officielle et documentee.
On s'appuie ici sur la librairie communautaire yfinance, qui elle-meme
consomme des endpoints non contractuels - susceptibles de changer sans
preavis (voir docs/17-limites-legales-techniques.md). C'est precisement
pour absorber ce risque que cette classe est isolee derriere l'interface
MarketDataProvider : un remplacement de source ne touche que ce fichier.
"""
from datetime import date

import yfinance as yf

from app.core.exceptions import DataProviderError
from app.domains.market_data.providers.base import MarketDataProvider, PriceBarDTO


class YahooFinanceProvider(MarketDataProvider):
    async def fetch_history(self, ticker: str, start: date, end: date) -> list[PriceBarDTO]:
        """
        Etape 19 : auto_adjust=False explicite. Par defaut, yfinance ajuste
        deja Close (et OHLC) pour les dividendes/splits (auto_adjust=True) et
        ne renvoie alors AUCUNE colonne "Adj Close" distincte - avant ce
        correctif, `close` et `adjusted_close` stockaient donc silencieusement
        la meme valeur (deja ajustee), et le vrai cours brut/cote n'etait
        jamais conserve. Avec auto_adjust=False : `close` = cours brut
        reellement cote ce jour-la (ce qu'on paierait en executant un ordre -
        voir portfolio/service.py), `adjusted_close` = cours retraite des
        dividendes/splits (a utiliser pour les calculs de rendement/backtesting,
        voir backtests/service.py et market_data/service.py).
        """
        try:
            history = yf.Ticker(ticker).history(
                start=start.isoformat(), end=end.isoformat(), interval="1d", auto_adjust=False
            )
        except Exception as exc:  # yfinance ne documente pas un type d'exception stable
            raise DataProviderError(f"Echec de recuperation Yahoo Finance pour {ticker}: {exc}") from exc

        if history.empty:
            return []

        bars: list[PriceBarDTO] = []
        for trade_date, row in history.iterrows():
            bars.append(
                PriceBarDTO(
                    trade_date=trade_date.date(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    adjusted_close=float(row["Adj Close"]) if "Adj Close" in row else float(row["Close"]),
                    volume=int(row["Volume"]),
                )
            )
        return bars
