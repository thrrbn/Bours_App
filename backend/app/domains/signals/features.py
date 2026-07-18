"""
Construction du vecteur de features utilise par le moteur de score, en
agregeant market_data (technique) et news (sentiment) pour un horizon donne.
Voir docs/11-strategie-scoring-hybride.md.
"""
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_data.repository import get_latest_indicators, get_price_history
from app.domains.news.service import get_sentiment_summary

HORIZON_NEWS_WINDOW_DAYS = {"short": 5, "medium": 30, "long": 180}


@dataclass
class SignalFeatures:
    horizon: str
    price_history_days: int
    trend_direction: str  # 'up' | 'down' | 'flat'
    rsi_14: float | None
    macd_cross: str  # 'bullish' | 'bearish' | 'none'
    volatility_20d: float | None
    news_sentiment: float
    news_article_count: int
    days_since_last_news: int | None


async def build_feature_vector(db: AsyncSession, asset_id: uuid.UUID, horizon: str) -> SignalFeatures:
    price_rows = await get_price_history(db, asset_id)
    indicators = await get_latest_indicators(db, asset_id)
    window_days = HORIZON_NEWS_WINDOW_DAYS.get(horizon, 30)
    news_summary = await get_sentiment_summary(db, asset_id, days=window_days)

    trend_direction = "flat"
    if indicators and indicators.sma_20 and indicators.sma_50:
        if float(indicators.sma_20) > float(indicators.sma_50):
            trend_direction = "up"
        elif float(indicators.sma_20) < float(indicators.sma_50):
            trend_direction = "down"

    macd_cross = "none"
    if indicators and indicators.macd is not None and indicators.macd_signal is not None:
        macd_cross = "bullish" if float(indicators.macd) > float(indicators.macd_signal) else "bearish"

    return SignalFeatures(
        horizon=horizon,
        price_history_days=len(price_rows),
        trend_direction=trend_direction,
        rsi_14=float(indicators.rsi_14) if indicators and indicators.rsi_14 is not None else None,
        macd_cross=macd_cross,
        volatility_20d=(
            float(indicators.volatility_20d) if indicators and indicators.volatility_20d is not None else None
        ),
        news_sentiment=news_summary["average_sentiment"],
        news_article_count=news_summary["article_count"],
        days_since_last_news=0 if news_summary["article_count"] else None,
    )
