import uuid
from datetime import date

from pydantic import BaseModel


class BacktestRunCreate(BaseModel):
    engine_version: str
    period_start: date
    period_end: date
    asset_ids: list[uuid.UUID]


class BacktestResultRead(BaseModel):
    asset_id: uuid.UUID
    horizon: str
    precision: float | None
    win_rate: float | None
    false_positive_rate: float | None
    max_drawdown: float | None
    signal_count: int
    sharpe_ratio: float | None = None
    calmar_ratio: float | None = None
    profit_factor: float | None = None
    avg_risk_reward: float | None = None
