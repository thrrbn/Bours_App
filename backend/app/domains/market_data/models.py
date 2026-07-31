import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PriceBar(Base):
    __tablename__ = "price_bars"
    __table_args__ = (UniqueConstraint("asset_id", "trade_date", name="uq_price_bar_asset_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    adjusted_close: Mapped[float | None] = mapped_column(Numeric(18, 6))
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="yahoo_finance")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Dividend(Base):
    """
    Historique des dividendes par actif (31/07/2026) - alimente le credit
    automatique de dividendes dans le portefeuille virtuel (voir
    portfolio/repository.py:dividends_credited_until et
    jobs/credit_dividends_job.py). Absent jusqu'ici : le portefeuille
    n'achetait/vendait qu'au cours brut, sans jamais recevoir le cash reel
    verse par une action a un detenteur au jour du detachement - ce qui
    sous-estimait le rendement total simule pour les titres a dividende
    (voir docs/STACK.md pour la discussion complete).
    """

    __tablename__ = "dividends"
    __table_args__ = (UniqueConstraint("asset_id", "ex_date", name="uq_dividend_asset_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_per_share: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"
    __table_args__ = (UniqueConstraint("asset_id", "trade_date", name="uq_indicator_asset_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    sma_20: Mapped[float | None] = mapped_column(Numeric(18, 6))
    sma_50: Mapped[float | None] = mapped_column(Numeric(18, 6))
    sma_200: Mapped[float | None] = mapped_column(Numeric(18, 6))
    ema_12: Mapped[float | None] = mapped_column(Numeric(18, 6))
    ema_26: Mapped[float | None] = mapped_column(Numeric(18, 6))
    rsi_14: Mapped[float | None] = mapped_column(Numeric(6, 3))
    macd: Mapped[float | None] = mapped_column(Numeric(18, 6))
    macd_signal: Mapped[float | None] = mapped_column(Numeric(18, 6))
    bollinger_upper: Mapped[float | None] = mapped_column(Numeric(18, 6))
    bollinger_lower: Mapped[float | None] = mapped_column(Numeric(18, 6))
    volatility_20d: Mapped[float | None] = mapped_column(Numeric(10, 6))
    momentum_roc_20: Mapped[float | None] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
