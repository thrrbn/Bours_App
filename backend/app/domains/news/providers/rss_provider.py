"""
Fournisseur de news base sur des flux RSS gratuits (Yahoo Finance, Google News).
Voir docs/08-pipeline-ingestion.md pour le detail du choix de source.
"""
import logging
from datetime import datetime, timezone

import feedparser
import httpx

from app.core.exceptions import DataProviderError
from app.domains.news.providers.base import NewsArticleDTO, NewsProvider

logger = logging.getLogger(__name__)

YAHOO_RSS_TEMPLATE = "https://finance.yahoo.com/rss/headline?s={ticker}"
GOOGLE_NEWS_RSS_TEMPLATE = "https://news.google.com/rss/search?q={query}"

# Yahoo Finance (et dans une moindre mesure Google News) bloquent agressivement
# les requetes dont le User-Agent ressemble a un client HTTP generique (le
# defaut d'httpx, "python-httpx/x.y.z", est immediatement reconnu comme non
# navigateur et renvoie un 429). Un User-Agent de navigateur reel reduit
# fortement ce blocage, meme si aucune garantie n'existe (voir
# docs/17-limites-legales-techniques.md sur la fragilite de ces sources).
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


class RssNewsProvider(NewsProvider):
    def __init__(self, timeout_seconds: float = 10.0):
        self._timeout = timeout_seconds

    async def fetch_articles(self, ticker: str, company_name: str) -> list[NewsArticleDTO]:
        """
        Interroge les TROIS flux independamment : si l'un echoue (bloque, en
        panne...), les autres continuent de fournir des resultats - principe
        de resilience par source (docs/08-pipeline-ingestion.md).
        """
        articles: list[NewsArticleDTO] = []

        try:
            articles.extend(
                await self._fetch_feed(YAHOO_RSS_TEMPLATE.format(ticker=ticker), source="yahoo_rss")
            )
        except DataProviderError as exc:
            logger.warning("Flux yahoo_rss indisponible pour %s: %s", ticker, exc)

        query = f"{company_name}+bourse".replace(" ", "+")
        try:
            articles.extend(
                await self._fetch_feed(GOOGLE_NEWS_RSS_TEMPLATE.format(query=query), source="google_news_rss")
            )
        except DataProviderError as exc:
            logger.warning("Flux google_news_rss indisponible pour %s: %s", ticker, exc)

        # 31/07/2026 : Yahoo Finance FR (fr.finance.yahoo.com) publie des
        # articles absents des deux flux ci-dessus (constat utilisateur).
        # Plutot que de deviner une URL RSS directe sur ce sous-domaine (non
        # verifiee, potentiellement inexistante - meme prudence que le reste
        # de ce fichier vis-a-vis des endpoints non contractuels, voir
        # docs/17), on reutilise le mecanisme Google News RSS DEJA
        # fonctionnel ci-dessus, avec l'operateur de recherche standard
        # `site:` pour ne remonter que des pages de ce sous-domaine - plus
        # fiable qu'un essai direct non teste.
        yahoo_fr_query = f"site:fr.finance.yahoo.com+{company_name}".replace(" ", "+")
        try:
            articles.extend(
                await self._fetch_feed(
                    GOOGLE_NEWS_RSS_TEMPLATE.format(query=yahoo_fr_query), source="google_news_yahoo_fr"
                )
            )
        except DataProviderError as exc:
            logger.warning("Flux google_news_yahoo_fr indisponible pour %s: %s", ticker, exc)

        return articles

    async def _fetch_feed(self, url: str, source: str) -> list[NewsArticleDTO]:
        try:
            # follow_redirects=True est indispensable : Yahoo et Google News
            # redirigent tous deux vers une URL canonique (301/302) - sans ce
            # flag, httpx leve une erreur explicite plutot que de suivre.
            async with httpx.AsyncClient(
                timeout=self._timeout, headers=DEFAULT_HEADERS, follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DataProviderError(f"Echec de recuperation du flux RSS {source}: {exc}") from exc

        parsed = feedparser.parse(response.text)
        articles: list[NewsArticleDTO] = []
        for entry in parsed.entries:
            published = entry.get("published_parsed")
            published_at = (
                datetime(*published[:6], tzinfo=timezone.utc) if published else datetime.now(timezone.utc)
            )
            articles.append(
                NewsArticleDTO(
                    source=source,
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    published_at=published_at,
                    raw_content=entry.get("summary"),
                )
            )
        return articles
