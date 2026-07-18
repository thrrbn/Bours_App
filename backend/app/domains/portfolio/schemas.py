import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domains.assets.schemas import AssetRead


class BuyRequest(BaseModel):
    asset_id: uuid.UUID
    quantity: float = Field(gt=0)


class SellRequest(BaseModel):
    asset_id: uuid.UUID
    quantity: float = Field(gt=0)


class PositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset: AssetRead
    quantity: float
    avg_cost: float
    current_price: float | None
    market_value: float | None
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset: AssetRead
    side: str
    quantity: float
    price: float
    total_amount: float
    realized_pnl: float | None
    price_date: date
    executed_at: datetime


class PortfolioSummaryRead(BaseModel):
    cash_balance: float
    starting_cash: float
    positions_value: float
    total_value: float
    total_pnl: float
    total_pnl_pct: float
    positions: list[PositionRead]
    disclaimer: str = (
        "Portefeuille de simulation - aucun ordre reel n'est passe, aucun argent reel n'est engage. "
        "Voir /api/v1/compliance/disclaimer."
    )
