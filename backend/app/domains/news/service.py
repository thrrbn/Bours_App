"""Orchestration : ingestion des articles, scoring de sentiment, extraction de mots-cles."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.news import repository
from app.domains.news.nlp.keywords import extract_keywords
from app.domains.news.nlp.sentiment import score_sentiment
from app.domains.news.providers.base import NewsProvider


async def ingest_and_score(
    db: AsyncSession, asset_id: uuid.UUID, ticker: str, company_name: str, provider: NewsProvider
) -> int:
    articles = await provider.fetch_articles(ticker, company_name)
    new_count = 0
    for article in articles:
        if await repository.exists_by_url(db, article.url):
            continue
        text_for_analysis = f"{article.title} {article.raw_content or ''}"
        sentiment = score_sentiment(text_for_analysis)
        keyword_matches = extract_keywords(text_for_analysis)
        await repository.create_article_with_keywords(
            db, asset_id=asset_id, article=article, sentiment=sentiment, keyword_matches=keyword_matches
        )
        new_count += 1
    return new_count


async def get_sentiment_summary(db: AsyncSession, asset_id: uuid.UUID, days: int = 7) -> dict:
    articles = await repository.get_recent_articles(db, asset_id, days=days)
    if not articles:
        return {"article_count": 0, "average_sentiment": 0.0, "dominant_keywords": []}

    scores = [float(a.sentiment_score) for a in articles if a.sentiment_score is not None]
    average_sentiment = sum(scores) / len(scores) if scores else 0.0
    dominant_keywords = await repository.get_dominant_keywords(db, [a.id for a in articles])
    return {
        "article_count": len(articles),
        "average_sentiment": average_sentiment,
        "dominant_keywords": dominant_keywords,
    }
