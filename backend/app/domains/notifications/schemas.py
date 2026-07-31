from datetime import datetime

from pydantic import BaseModel

from app.domains.assets.schemas import AssetRead

BRIEFING_DISCLAIMER = (
    "Synthese automatique (sentiment lexical + mots-cles + signal statistique), en francais, a partir de sources "
    "tierces citees pour chaque titre - pas une recommandation de cette application. Voir /api/v1/compliance/disclaimer."
)


class BriefingSignalItem(BaseModel):
    horizon: str
    horizon_label: str
    signal: str
    signal_label: str
    changed_since_last_briefing: bool


class BriefingKeywordItem(BaseModel):
    keyword: str
    weight: float
    horizon_impact: str
    occurrences: int


class BriefingArticleRef(BaseModel):
    title: str
    url: str
    source: str
    published_at: datetime


class BriefingAssetItem(BaseModel):
    asset: AssetRead
    held: bool
    watched: bool
    quantity_held: float | None
    signals: list[BriefingSignalItem]
    article_count: int
    average_sentiment: float
    sentiment_label: str
    keywords: list[BriefingKeywordItem]
    consensus_label: str | None
    latest_article: BriefingArticleRef | None
    highlight_note: str


class BriefingRead(BaseModel):
    generated_at: datetime
    window_days: int
    items: list[BriefingAssetItem]
    disclaimer: str = BRIEFING_DISCLAIMER
