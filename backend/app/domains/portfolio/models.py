"""
Portefeuille virtuel de simulation (Etape 12) : aucun lien avec un compte de
courtage reel, purement pedagogique. Mono-portefeuille (comme la watchlist,
voir watchlist/models.py) - une seule ligne PortfolioState fait office de
singleton, cree a la premiere utilisation avec le cash de depart configure
(settings.portfolio_starting_cash).
"""
import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domains.assets.models import Asset


class PortfolioState(Base):
    __tablename__ = "portfolio_state"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cash_balance: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    starting_cash: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    avg_cost: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    asset: Mapped[Asset] = relationship(Asset, lazy="joined")


class PortfolioTransaction(Base):
    __tablename__ = "portfolio_transactions"
    __table_args__ = (UniqueConstraint("id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # 'buy' | 'sell'
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    realized_pnl: Mapped[float | None] = mapped_column(Numeric(18, 2))
    price_date: Mapped[date] = mapped_column(nullable=False)  # date du dernier cours utilise, pas la date d'execution
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped[Asset] = relationship(Asset, lazy="joined")
