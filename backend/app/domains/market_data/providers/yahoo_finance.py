"""
Implementation Yahoo Finance du MarketDataProvider.

Attention : Yahoo Finance n'expose pas d'API officielle et documentee.
On s'appuie ici sur la librairie communautaire yfinance, qui elle-meme
consomme des endpoints non contractuels - susceptibles de changer sans
preavis (voir docs/17-limites-legales-techniques.md). C'est precisement
pour absorber ce risque que cette classe est isolee derriere l'interface
MarketDataProvider : un remplacement de source ne touche que ce fichier.
"""
import math
from datetime import date

import yfinance as yf

from app.core.exceptions import DataProviderError
from app.domains.market_data.providers.base import DividendDTO, MarketDataProvider, PriceBarDTO


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
            close = float(row["Close"])
            open_ = float(row["Open"])
            high = float(row["High"])
            low = float(row["Low"])
            # Bug reel trouve le 30/07/2026 : yfinance renvoie parfois une
            # ligne avec des OHLC a NaN (frequent pour la bougie du jour
            # encore en formation avant cloture, ou un jour peu liquide).
            # float(nan) ne leve AUCUNE exception - sans ce garde-fou, un NaN
            # se glissait silencieusement dans price_bars.close, puis dans le
            # cout de revient (avg_cost) et le cash du portefeuille virtuel a
            # l'achat (portfolio/service.py), qui restait ensuite corrompu
            # (NaN) indefiniment - voir docs/STACK.md. On ignore la ligne
            # plutot que de stocker un cours invalide.
            if any(math.isnan(v) for v in (open_, high, low, close)):
                continue
            bars.append(
                PriceBarDTO(
                    trade_date=trade_date.date(),
                    open=open_,
                    high=high,
                    low=low,
                    close=close,
                    adjusted_close=float(row["Adj Close"]) if "Adj Close" in row else close,
                    volume=int(row["Volume"]) if not math.isnan(row["Volume"]) else 0,
                )
            )
        return bars

    async def fetch_dividends(self, ticker: str) -> list[DividendDTO]:
        """
        31/07/2026 : historique complet des dividendes verses (yfinance expose
        `Ticker.dividends`, une Series pandas indexee par date de detachement,
        valeur = montant BRUT par action). Utilise pour crediter le
        portefeuille virtuel (voir jobs/credit_dividends_job.py) - sans clé
        d'API, meme mecanisme non contractuel que fetch_history (voir
        docstring de module).
        """
        try:
            series = yf.Ticker(ticker).dividends
        except Exception as exc:
            raise DataProviderError(f"Echec de recuperation des dividendes Yahoo Finance pour {ticker}: {exc}") from exc

        if series is None or series.empty:
            return []

        return [
            DividendDTO(ex_date=ex_date.date(), amount_per_share=float(amount))
            for ex_date, amount in series.items()
            if not math.isnan(amount) and amount > 0
        ]
