"""
Etat du briefing quotidien (31/07/2026) - memorise le dernier signal INCLUS
dans un briefing REELLEMENT genere (envoi reel ou declenchement manuel avec
persist_state=True, voir briefing_service.py), par actif et par horizon.
Delibperement SEPARE de notifications.models.NotificationState (qui
appartient au job de changement de signal sur la watchlist, voir service.py)
pour ne pas melanger les deux mecanismes de suivi - meme si les deux
observent le meme Signal, ils repondent a des questions differentes
("un changement watchlist a-t-il deja ete notifie ?" vs "ce signal
figurait-il deja dans le dernier briefing envoye ?").
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BriefingAssetState(Base):
    __tablename__ = "briefing_asset_states"
    __table_args__ = (UniqueConstraint("asset_id", "horizon", name="uq_briefing_state_asset_horizon"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    horizon: Mapped[str] = mapped_column(String(20), nullable=False)
    last_signal: Mapped[str] = mapped_column(String(30), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
