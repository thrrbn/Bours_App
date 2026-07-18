"""Acces aux donnees news - persistance, deduplication, agregation simple."""
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
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
