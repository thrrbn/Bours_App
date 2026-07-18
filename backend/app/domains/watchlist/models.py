"""
Watchlist : liste des actifs suivis, utilisee a la fois pour les notifications
email (Etape 11) et comme base du dashboard / futur portefeuille virtuel
(Etape 12). Volontairement sans user_id : l'application reste mono-utilisateur
en V1 (voir users/auth.py), une seule watchlist partagee suffit - le multi-
utilisateur (colonne user_id, deja anticipee dans db/migrations/001_init.sql)
sera ajoute si le besoin se confirme, pas avant.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domains.assets.models import Asset


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    notify_on_change: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped[Asset] = relationship(Asset, lazy="joined")
