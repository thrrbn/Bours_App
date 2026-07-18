import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NewsArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    title: str
    url: str
    published_at: datetime
    sentiment_score: float | None
    sentiment_method: str | None


class SentimentSummary(BaseModel):
    article_count: int
    average_sentiment: float
    dominant_keywords: list[str]
