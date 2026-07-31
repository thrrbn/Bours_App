"""Acces aux donnees news - persistance, deduplication, agregation simple."""
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.news.models import NewsArticle, NewsKeywordMatch
from app.domains.news.nlp.keywords import KeywordMatch
from app.domains.news.providers.base import NewsArticleDTO


async def exists_by_url(db: AsyncSession, url: str) -> bool:
    stmt = select(NewsArticle.id).where(NewsArticle.url == url)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create_article_with_keywords(
    db: AsyncSession,
    asset_id: uuid.UUID,
    article: NewsArticleDTO,
    sentiment: float,
    keyword_matches: list[KeywordMatch],
) -> NewsArticle:
    db_article = NewsArticle(
        asset_id=asset_id,
        source=article.source,
        title=article.title,
        url=article.url,
        published_at=article.published_at,
        raw_content=article.raw_content,
        sentiment_score=sentiment,
        sentiment_method="lexicon_v1",
    )
    db.add(db_article)
    await db.flush()  # recupere db_article.id sans committer

    for match in keyword_matches:
        db.add(
            NewsKeywordMatch(
                article_id=db_article.id,
                keyword=match.keyword,
                weight=match.weight,
                horizon_impact=match.horizon_impact,
                occurrences=match.occurrences,
            )
        )
    await db.commit()
    await db.refresh(db_article)
    return db_article


async def get_article_by_id(db: AsyncSession, article_id: uuid.UUID) -> NewsArticle | None:
    return await db.get(NewsArticle, article_id)


async def get_keyword_matches_for_article(db: AsyncSession, article_id: uuid.UUID) -> list[NewsKeywordMatch]:
    stmt = select(NewsKeywordMatch).where(NewsKeywordMatch.article_id == article_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_all_articles(db: AsyncSession, asset_id: uuid.UUID | None = None) -> list[NewsArticle]:
    """Tous les articles connus (pas de fenetre de date) - utilise par
    service.py::rescan_keywords pour repasser l'existant au lexique ACTUEL
    sans reingerer (voir docstring de rescan_keywords)."""
    stmt = select(NewsArticle)
    if asset_id is not None:
        stmt = stmt.where(NewsArticle.asset_id == asset_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def replace_keyword_matches(
    db: AsyncSession, article: NewsArticle, sentiment: float, keyword_matches: list[KeywordMatch]
) -> None:
    """Remplace les NewsKeywordMatch d'un article deja stocke et met a jour
    son sentiment_score - contrairement a create_article_with_keywords
    (nouvel article), ici l'article existe deja (voir rescan_keywords)."""
    await db.execute(delete(NewsKeywordMatch).where(NewsKeywordMatch.article_id == article.id))
    article.sentiment_score = sentiment
    for match in keyword_matches:
        db.add(
            NewsKeywordMatch(
                article_id=article.id,
                keyword=match.keyword,
                weight=match.weight,
                horizon_impact=match.horizon_impact,
                occurrences=match.occurrences,
            )
        )
    await db.commit()


async def get_recent_articles(db: AsyncSession, asset_id: uuid.UUID, days: int = 7) -> list[NewsArticle]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(NewsArticle)
        .where(NewsArticle.asset_id == asset_id, NewsArticle.published_at >= since)
        .order_by(NewsArticle.published_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_dominant_keywords(db: AsyncSession, article_ids: list[uuid.UUID], top_n: int = 5) -> list[str]:
    if not article_ids:
        return []
    stmt = select(NewsKeywordMatch.keyword).where(NewsKeywordMatch.article_id.in_(article_ids))
    result = await db.execute(stmt)
    counter = Counter(result.scalars().all())
    return [keyword for keyword, _ in counter.most_common(top_n)]


async def get_articles_by_keywords(
    db: AsyncSession, keywords: list[str], limit: int = 50
) -> list[tuple[NewsArticle, NewsKeywordMatch]]:
    """Articles (toutes dates, tous actifs) dont au moins un NewsKeywordMatch
    correspond a l'un des `keywords` donnes, les plus recents en premier -
    utilise par service.py::get_keyword_matches (voir aussi router.py: GET
    /news/keyword-matches) pour repondre concretement a "ou est-ce que ca
    apparait" pour un mot-cle personnalise. Si un article matche plusieurs
    des `keywords` demandes, il apparait une fois par mot-cle matche (join,
    pas de deduplication) - permet d'afficher CHAQUE mot-cle trouve."""
    if not keywords:
        return []
    stmt = (
        select(NewsArticle, NewsKeywordMatch)
        .join(NewsKeywordMatch, NewsKeywordMatch.article_id == NewsArticle.id)
        .where(NewsKeywordMatch.keyword.in_(keywords))
        .order_by(NewsArticle.published_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def get_keyword_counts(db: AsyncSession, article_ids: list[uuid.UUID], top_n: int = 5) -> list[tuple[str, int]]:
    """Comme get_dominant_keywords, mais garde le nombre d'articles ou chaque
    mot-cle apparait - utilise par notifications/briefing_service.py pour
    afficher "detecte dans N article(s)" plutot qu'une simple liste de noms."""
    if not article_ids:
        return []
    stmt = select(NewsKeywordMatch.keyword).where(NewsKeywordMatch.article_id.in_(article_ids))
    result = await db.execute(stmt)
    counter = Counter(result.scalars().all())
    return counter.most_common(top_n)
