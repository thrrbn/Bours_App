"""
Decouverte de titres candidats non encore suivis - PAS une recommandation
d'investissement (voir docs/17-limites-legales-techniques.md et le domaine
`compliance`) : cette liste ne fait que remonter des FAITS objectifs
(presence dans un palmares Yahoo Finance base sur le volume d'echanges,
frequence et ton moyen des articles RSS existants) pour que l'utilisateur
decide lui-meme s'il veut suivre un titre. Rien n'est jamais ajoute
automatiquement a `assets` - voir service.discover_candidates() et
router.py, endpoint en lecture seule (GET), aucun effet de bord en base.

Deux sources :
  1. Le screener Yahoo Finance integre a yfinance (`yf.screen("most_actives")`)
     - meme dependance et meme session/gestion de cookie-crumb que
     market_data/providers/yahoo_finance.py pour l'historique de prix.
     PAS d'appel HTTP fait main vers les endpoints Yahoo non officiels
     (/v1/finance/trending, /v7/finance/quote) : un essai direct s'est
     heurte a une erreur 403 (protection anti-bot / crumb requis - voir
     docs/17), alors que yfinance negocie deja cette authentification en
     interne pour ses propres besoins. Reutiliser cette negociation deja
     eprouvee est plus fiable que la reimplementer.
  2. Les flux RSS deja utilises par le domaine `news` (RssNewsProvider) et
     le meme scorer de sentiment lexical (news/nlp/sentiment.py) - reutilises
     tels quels, aucune logique NLP dupliquee ici.

Point de vigilance (voir docs/STACK.md) : yfinance expose `screen()` /
`PREDEFINED_SCREENER_QUERIES` depuis une version relativement recente du
package (bien apres 0.2.40, la borne minimale de requirements.txt) - un
`docker compose build` qui reutiliserait une image deja construite avec une
vieille version resolue pourrait ne pas avoir cette fonction. Verifier
`python -c "import yfinance; print(yfinance.__version__)"` dans le conteneur
si `AttributeError: module 'yfinance' has no attribute 'screen'`.
"""
import logging

import yfinance as yf

from app.core.exceptions import DataProviderError
from app.domains.news.nlp.sentiment import score_sentiment
from app.domains.news.providers.rss_provider import RssNewsProvider

logger = logging.getLogger(__name__)

# Correspondance approximative code/nom Yahoo -> libelle marche utilise
# ailleurs dans le projet (seed_data_us.py). Purement indicatif : l'utilisateur
# choisit/corrige le market exact au moment ou il ajoute vraiment l'actif
# via POST /api/v1/assets.
_EXCHANGE_TO_MARKET = {
    "NMS": "NASDAQ",
    "NGM": "NASDAQ",
    "NCM": "NASDAQ",
    "NYQ": "NYSE",
    "PCX": "NYSE",
    "ASE": "NYSE",
}

# Suffixe de ticker (convention Yahoo Finance) -> market utilise ailleurs
# dans le projet (seed_data_cac40.py/seed_data_dax.py/seed_data_aex.py) -
# verifie AVANT le code d'exchange Yahoo ci-dessus : plus fiable pour les
# places europeennes, ou `quote.get("exchange")` renvoie des codes non
# couverts par _EXCHANGE_TO_MARKET (ex. "PAR", "BRU", "GER" selon les
# versions de yfinance, jamais garanti - voir docs/17).
_SUFFIX_TO_MARKET = {
    ".PA": "EURONEXT_PARIS",
    ".BR": "EURONEXT_BRUSSELS",
    ".AS": "EURONEXT_AMSTERDAM",
    ".DE": "XETRA",
}


def guess_market(quote: dict, ticker: str | None = None) -> str:
    """Fonction pure, reutilisee aussi par fundamentals_provider.py (recherche
    live d'un ticker non suivi, voir service.py::lookup_ticker) - meme dict
    'quote'/'info' shape (cles exchange/fullExchangeName communes aux
    reponses yf.screen(...) et Ticker(...).info). `ticker` est optionnel
    (absent des reponses screener, mais toujours connu lors d'un lookup
    direct) - son suffixe est verifie en premier, plus fiable pour les
    places europeennes que le code d'exchange Yahoo."""
    if ticker:
        upper = ticker.upper()
        for suffix, market in _SUFFIX_TO_MARKET.items():
            if upper.endswith(suffix):
                return market
    exchange = quote.get("exchange", "")
    if exchange in _EXCHANGE_TO_MARKET:
        return _EXCHANGE_TO_MARKET[exchange]
    full_name = (quote.get("fullExchangeName") or "").lower()
    if "nasdaq" in full_name:
        return "NASDAQ"
    if "nyse" in full_name:
        return "NYSE"
    return "US_AUTRE"


def parse_screener_quotes(payload: dict) -> list[dict]:
    """Fonction pure - extrait [{symbol, name, market_guess}] d'une reponse
    yf.screen(...) (dict avec une cle "quotes", voir yfinance/screener/screener.py)."""
    quotes = payload.get("quotes") if isinstance(payload, dict) else None
    if not quotes:
        return []
    out = []
    for quote in quotes:
        symbol = quote.get("symbol")
        if not symbol:
            continue
        name = quote.get("shortName") or quote.get("longName") or symbol
        out.append({"symbol": symbol, "name": name, "market_guess": guess_market(quote, ticker=symbol)})
    return out


async def fetch_screener_candidates(query: str = "most_actives", count: int = 25) -> list[dict]:
    """Appel bloquant (comme yf.Ticker(...).history() dans yahoo_finance.py -
    meme convention deja acceptee dans ce projet, pas d'executor dedie)."""
    try:
        payload = yf.screen(query, count=count)
    except Exception as exc:  # yfinance ne documente pas un type d'exception stable
        raise DataProviderError(f"Echec du screener Yahoo Finance ({query}): {exc}") from exc
    return parse_screener_quotes(payload)


async def score_candidate_sentiment(ticker: str, company_name: str) -> tuple[int, float]:
    """Reutilise le meme flux RSS + scorer lexical que le domaine `news`
    (voir news/service.py:ingest_and_score), sans rien persister en base -
    ce candidat n'est pas (encore) un Asset suivi."""
    provider = RssNewsProvider()
    try:
        articles = await provider.fetch_articles(ticker, company_name)
    except Exception:
        logger.warning("Echec de recuperation RSS pour le candidat %s", ticker, exc_info=True)
        return 0, 0.0
    if not articles:
        return 0, 0.0
    scores = [score_sentiment(f"{a.title} {a.raw_content or ''}") for a in articles]
    return len(articles), sum(scores) / len(scores)


async def discover_candidates(
    tracked_tickers: set[str], query: str = "most_actives", screener_count: int = 25, max_candidates: int = 10
) -> list[dict]:
    """
    Orchestration complete : screener Yahoo Finance -> filtre des tickers
    deja suivis -> sentiment RSS recent, pour au plus `max_candidates` titres
    (chaque candidat declenche 2 requetes RSS - voir RssNewsProvider - donc
    ce nombre est volontairement borne). Retourne des dicts prets pour
    CandidateAssetRead (voir schemas.py).
    """
    try:
        quotes = await fetch_screener_candidates(query=query, count=screener_count)
    except DataProviderError:
        logger.warning("Screener Yahoo Finance indisponible, aucune suggestion", exc_info=True)
        return []

    new_candidates = [q for q in quotes if q["symbol"].upper() not in tracked_tickers][:max_candidates]

    results = []
    for candidate in new_candidates:
        mention_count, average_sentiment = await score_candidate_sentiment(
            candidate["symbol"], candidate["name"]
        )
        results.append(
            {
                "ticker": candidate["symbol"],
                "name": candidate["name"],
                "market_guess": candidate["market_guess"],
                "mention_count": mention_count,
                "average_sentiment": round(average_sentiment, 3),
            }
        )
    return results
