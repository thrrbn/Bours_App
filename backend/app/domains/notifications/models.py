"""
Etat de notification : memorise le dernier signal pour lequel un email a deja
ete envoye, par actif et par horizon - c'est ce qui permet de ne notifier que
sur un CHANGEMENT de signal, jamais de renvoyer le meme email en boucle a
chaque execution du job planifie.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationState(Base):
    __tablename__ = "notification_states"
    __table_args__ = (UniqueConstraint("asset_id", "horizon", name="uq_notification_state_asset_horizon"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    horizon: Mapped[str] = mapped_column(String(20), nullable=False)
    last_notified_signal: Mapped[str] = mapped_column(String(30), nullable=False)
    last_notified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
