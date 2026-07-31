"""
Implementation Binance du MarketDataProvider.

Utilise uniquement l'endpoint public /api/v3/klines (donnees de marche en
lecture seule, aucune cle API, aucun ordre) : voir docs/17-limites-legales-
techniques.md, meme logique de prudence que pour Yahoo Finance. Ce fichier
ne fait QUE de la lecture de cours - le passage d'ordres reels (Binance ou
tout autre courtier) est hors perimetre de ce provider et n'est implemente
nulle part dans ce projet.

Reference API publique : https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints
"""
from datetime import date, datetime, timezone

import httpx

from app.core.exceptions import DataProviderError
from app.domains.market_data.providers.base import MarketDataProvider, PriceBarDTO

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
# Limite Binance par appel ; largement suffisant vu days_back=400 par defaut
# (market_data/service.py:ingest_history) - pas de pagination necessaire ici.
_MAX_KLINES_PER_CALL = 1000


def _to_ms(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def parse_klines(raw: list) -> list[PriceBarDTO]:
    """
    Transforme la reponse brute /klines (liste de listes positionnelles) en
    PriceBarDTO. Fonction pure, isolee de l'appel reseau pour rester testable
    sans mock HTTP (meme principe que compute_indicators_dataframe).

    Format d'une entree Binance (voir doc API) :
    [openTime, open, high, low, close, volume, closeTime, quoteVolume,
     trades, takerBuyBase, takerBuyQuote, ignore]
    """
    bars: list[PriceBarDTO] = []
    for entry in raw:
        open_time_ms, o, h, l, c, v = entry[0], entry[1], entry[2], entry[3], entry[4], entry[5]
        trade_date = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc).date()
        close = float(c)
        bars.append(
            PriceBarDTO(
                trade_date=trade_date,
                open=float(o),
                high=float(h),
                low=float(l),
                close=close,
                # Pas de dividendes/splits en crypto : le cours ajuste = le cours brut.
                adjusted_close=close,
                volume=int(float(v)),
            )
        )
    return bars


class BinanceProvider(MarketDataProvider):
    async def fetch_history(self, ticker: str, start: date, end: date) -> list[PriceBarDTO]:
        params = {
            "symbol": ticker.upper(),
            "interval": "1d",
            "startTime": _to_ms(start),
            "endTime": _to_ms(end),
            "limit": _MAX_KLINES_PER_CALL,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(BINANCE_KLINES_URL, params=params)
                response.raise_for_status()
                raw = response.json()
        except httpx.HTTPError as exc:
            raise DataProviderError(f"Echec de recuperation Binance pour {ticker}: {exc}") from exc

        return parse_klines(raw)
