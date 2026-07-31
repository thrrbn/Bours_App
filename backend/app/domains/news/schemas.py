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


class CustomKeywordCreate(BaseModel):
    keyword: str
    weight: float = 0.0
    horizon_impact: str = "medium"


class CustomKeywordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    keyword: str
    weight: float
    horizon_impact: str
    created_at: datetime


class KeywordMatchRead(BaseModel):
    """Un article precis qui matche un mot-cle personnalise - voir
    service.py::get_keyword_matches. `asset_ticker`/`asset_name` peuvent etre
    None si l'actif source a ete retire depuis (voir assets/service.py::
    delete_asset, qui ne supprime jamais l'historique news)."""

    keyword: str
    weight: float
    horizon_impact: str
    occurrences: int
    article: NewsArticleRead
    asset_ticker: str | None
    asset_name: str | None
