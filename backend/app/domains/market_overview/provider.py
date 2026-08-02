"""
Donnees "Marche" (01/08/2026, revu le meme jour) : indices + plus fortes
hausses/baisses, TOUJOURS EN DIRECT depuis des sources de reference externes
et gratuites - jamais limitees aux actifs personnellement suivis dans cette
application (demande explicite : "je voudrais pour marche les valeurs
donnees par yahoo et binance et pas seul celle present dans mon
application"). Trois sources :

  1. Indices (INDEX_DEFINITIONS ci-dessous) - yfinance (Ticker.info), meme
     mecanisme que fundamentals_provider.py.
  2. Etats-Unis - le screener officiel Yahoo Finance integre a yfinance
     (yf.screen("day_gainers"/"day_losers")) - deja utilise et eprouve dans
     ce projet par assets/discovery.py::fetch_screener_candidates. Couvre le
     marche US reel, pas seulement les megacaps seedees ici.
  3. France - Yahoo Finance n'expose pas de screener gainers/losers scope a
     Euronext Paris via yfinance (les requetes predefinies sont US par
     defaut) - a defaut, on interroge en direct la composition officielle du
     CAC 40 (assets/seed_data_cac40.py, ~39 valeurs) et on calcule nous-meme
     les hausses/baisses a partir de cotations LIVE - toujours independant
     de ce que l'utilisateur suit personnellement dans l'app.
  4. Crypto - API publique Binance /ticker/24hr (aucune cle, lecture seule,
     meme categorie que market_data/providers/binance.py) - couvre TOUTES
     les paires USDT cotees sur Binance, filtrees par un volume 24h minimum
     pour eviter que des paires illiquides/exotiques ne dominent le
     classement (bruit, pas representatif d'un "marche").

Chaque ligne renvoyee inclut une URL vers la fiche de cotation de la source
(Yahoo Finance ou Binance) - voir yahoo_quote_url()/binance_trade_url() -
pour permettre un acces direct a la reference gratuite d'origine (demande
explicite de l'utilisateur), cette application ne se substituant a aucun
moment a ces sources.
"""
import logging

import httpx
import yfinance as yf

from app.domains.assets.seed_data_cac40 import CAC40_ASSETS

logger = logging.getLogger(__name__)

TOP_N = 5

# Choix delibere : CAC 40 + BEL 20 (public belge de l'app, voir
# docker-compose.yml/PGADMIN_DEFAULT_EMAIL) + Euro Stoxx 50 pour le contexte
# europeen, puis les 3 indices US majeurs.
INDEX_DEFINITIONS: list[dict] = [
    {"ticker": "^FCHI", "label": "CAC 40", "zone": "France"},
    {"ticker": "^BFX", "label": "BEL 20", "zone": "Belgique"},
    {"ticker": "^STOXX50E", "label": "Euro Stoxx 50", "zone": "Europe"},
    {"ticker": "^GSPC", "label": "S&P 500", "zone": "Etats-Unis"},
    {"ticker": "^IXIC", "label": "Nasdaq Composite", "zone": "Etats-Unis"},
    {"ticker": "^DJI", "label": "Dow Jones", "zone": "Etats-Unis"},
]

BINANCE_24H_URL = "https://api.binance.com/api/v3/ticker/24hr"
# Volume 24h minimum (en USDT) pour qu'une paire entre dans le classement -
# ecarte les paires exotiques/illiquides dont un mouvement de +/-80% ne
# reflete qu'un carnet d'ordres vide, pas un "marche" au sens ou l'entend
# cette page (meme esprit que seed_data_binance.py : "jamais un ecran de
# cotation generaliste").
BINANCE_MIN_QUOTE_VOLUME = 5_000_000


def _safe_float(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def yahoo_quote_url(ticker: str, market: str = "us") -> str:
    """URL de la fiche Yahoo Finance officielle et gratuite pour ce ticker -
    "^" doit etre encode (%5E) pour les indices."""
    encoded = ticker.replace("^", "%5E")
    domain = "fr.finance.yahoo.com" if market == "fr" else "finance.yahoo.com"
    return f"https://{domain}/quote/{encoded}"


def binance_trade_url(symbol: str) -> str:
    """URL de la fiche Binance officielle et gratuite pour cette paire."""
    if symbol.endswith("USDT"):
        return f"https://www.binance.com/en/trade/{symbol[:-4]}_USDT"
    return f"https://www.binance.com/en/trade/{symbol}"


def fetch_index_quotes() -> list[dict]:
    """
    Cotation courante (regularMarketPrice/regularMarketChangePercent - champs
    LIVE de yfinance, pas une cloture de la veille) pour chaque indice de
    INDEX_DEFINITIONS. Un indice indisponible est simplement omis du
    resultat plutot que de faire echouer tout le rafraichissement.
    """
    quotes: list[dict] = []
    for definition in INDEX_DEFINITIONS:
        try:
            info = yf.Ticker(definition["ticker"]).info
        except Exception:
            logger.warning("Echec de recuperation de l'indice %s", definition["ticker"], exc_info=True)
            continue

        last_price = _safe_float(info.get("regularMarketPrice")) if info else None
        if last_price is None:
            logger.warning("Indice %s: reponse Yahoo Finance sans cours exploitable", definition["ticker"])
            continue

        market = "fr" if definition["zone"] == "France" else "us"
        quotes.append(
            {
                "ticker": definition["ticker"],
                "label": definition["label"],
                "zone": definition["zone"],
                "last_price": last_price,
                "change_pct": _safe_float(info.get("regularMarketChangePercent")),
                "currency": info.get("currency"),
                "url": yahoo_quote_url(definition["ticker"], market=market),
            }
        )
    return quotes


def _screener_rows(query: str) -> list[dict]:
    try:
        payload = yf.screen(query, count=TOP_N)
    except Exception:
        logger.warning("Echec du screener US Yahoo Finance (%s)", query, exc_info=True)
        return []

    quotes = payload.get("quotes") if isinstance(payload, dict) else None
    if not quotes:
        return []

    rows = []
    for quote in quotes:
        symbol = quote.get("symbol")
        last_price = _safe_float(quote.get("regularMarketPrice"))
        if not symbol or last_price is None:
            continue
        rows.append(
            {
                "ticker": symbol,
                "name": quote.get("shortName") or quote.get("longName") or symbol,
                "last_price": last_price,
                "change_pct": _safe_float(quote.get("regularMarketChangePercent")),
                "currency": quote.get("currency"),
                "url": yahoo_quote_url(symbol, market="us"),
            }
        )
    return rows


def fetch_us_movers() -> dict:
    """
    Plus fortes hausses/baisses reelles du marche US, via les listes
    officielles "day_gainers"/"day_losers" du screener Yahoo Finance (meme
    mecanisme, deja eprouve, que assets/discovery.py::fetch_screener_candidates)
    - couvre l'integralite du marche US suivi par Yahoo, pas seulement les
    tickers seedes dans cette application.
    """
    return {"gainers": _screener_rows("day_gainers"), "losers": _screener_rows("day_losers")}


def fetch_fr_movers() -> dict:
    """
    Plus fortes hausses/baisses parmi la composition officielle du CAC 40
    (assets/seed_data_cac40.py), interrogee en DIRECT (pas depuis la base de
    cette application - voir le module docstring). yfinance ne propose pas
    de screener gainers/losers scope a Euronext Paris, d'ou cette approche
    "liste connue + cotation live" plutot qu'un screener generique US.
    """
    rows: list[dict] = []
    for entry in CAC40_ASSETS:
        ticker = entry["ticker"]
        try:
            info = yf.Ticker(ticker).info
        except Exception:
            logger.warning("Echec cotation CAC40 pour %s", ticker, exc_info=True)
            continue
        last_price = _safe_float(info.get("regularMarketPrice")) if info else None
        change_pct = _safe_float(info.get("regularMarketChangePercent")) if info else None
        if last_price is None or change_pct is None:
            continue
        rows.append(
            {
                "ticker": ticker,
                "name": entry["name"],
                "last_price": last_price,
                "change_pct": change_pct,
                "currency": entry.get("currency"),
                "url": yahoo_quote_url(ticker, market="fr"),
            }
        )

    gainers = sorted((r for r in rows if r["change_pct"] > 0), key=lambda r: r["change_pct"], reverse=True)[:TOP_N]
    losers = sorted((r for r in rows if r["change_pct"] < 0), key=lambda r: r["change_pct"])[:TOP_N]
    return {"gainers": gainers, "losers": losers}


async def fetch_crypto_movers() -> dict:
    """
    Plus fortes hausses/baisses parmi TOUTES les paires USDT cotees sur
    Binance (endpoint public /ticker/24hr, aucune cle - voir
    market_data/providers/binance.py pour le meme choix de source), filtrees
    par volume 24h minimum (BINANCE_MIN_QUOTE_VOLUME) pour ecarter le bruit
    des paires illiquides.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(BINANCE_24H_URL)
            response.raise_for_status()
            raw = response.json()
    except httpx.HTTPError:
        logger.warning("Echec de recuperation Binance /ticker/24hr", exc_info=True)
        return {"gainers": [], "losers": []}

    rows: list[dict] = []
    for entry in raw:
        symbol = entry.get("symbol", "")
        if not symbol.endswith("USDT"):
            continue
        quote_volume = _safe_float(entry.get("quoteVolume"))
        if quote_volume is None or quote_volume < BINANCE_MIN_QUOTE_VOLUME:
            continue
        change_pct = _safe_float(entry.get("priceChangePercent"))
        last_price = _safe_float(entry.get("lastPrice"))
        if change_pct is None or last_price is None:
            continue
        rows.append(
            {
                "ticker": symbol,
                "name": symbol[:-4],
                "last_price": last_price,
                "change_pct": change_pct,
                "currency": "USDT",
                "url": binance_trade_url(symbol),
            }
        )

    gainers = sorted((r for r in rows if r["change_pct"] > 0), key=lambda r: r["change_pct"], reverse=True)[:TOP_N]
    losers = sorted((r for r in rows if r["change_pct"] < 0), key=lambda r: r["change_pct"])[:TOP_N]
    return {"gainers": gainers, "losers": losers}
