import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    horizon: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    technical_score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    news_score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    risk_score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    final_signal: Mapped[str] = mapped_column(String(30), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False)


class SignalExplanation(Base):
    __tablename__ = "signal_explanations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("signals.id", ondelete="CASCADE"), index=True
    )
    component: Mapped[str] = mapped_column(String(50), nullable=False)
    contribution_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    text_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
