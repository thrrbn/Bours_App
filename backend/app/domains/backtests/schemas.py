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
    # 31/07/2026 : integration backtesting.py (voir kernc_engine.py).
    # strategy_name distingue "internal_rules" du nouveau moteur ; extra_metrics
    # porte les statistiques riches de backtesting.py sans equivalent type
    # ci-dessus (Sortino, Exposure Time, SQN, Best/Worst Trade...).
    strategy_name: str | None = None
    extra_metrics: dict | None = None
