import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.assets.schemas import AssetRead
from app.domains.news.schemas import NewsArticleRead


class AnalystConsensusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset: AssetRead
    strong_buy: int
    buy: int
    hold: int
    sell: int
    strong_sell: int
    consensus_score: float
    consensus_label: str
    fetched_at: datetime
    source: str = "yahoo_finance"
    disclaimer: str = (
        "Avis d'analystes externes (Yahoo Finance), pas une recommandation de cette application. "
        "Voir /api/v1/compliance/disclaimer."
    )


class PortfolioAlertRead(BaseModel):
    asset: AssetRead
    consensus_label: str
    consensus_score: float
    quantity_held: float
    avg_cost: float
    current_price: float | None
    note: str


class ComparisonRead(BaseModel):
    asset: AssetRead
    horizon: str
    internal_rules_signal: str
    internal_rules_direction: str
    internal_ml_status: str | None
    internal_ml_direction: str | None
    external_consensus_label: str | None
    external_consensus_score: float | None
    agreement_rules: bool | None
    agreement_ml: bool | None
    recent_articles: list[NewsArticleRead]
    note: str
