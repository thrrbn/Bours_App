"""
Consensus d'analystes externes (source: Yahoo Finance, via yfinance) - une
donnee TIERCE, jamais notre propre recommandation. Toujours affichee avec sa
source et un disclaimer (voir docs/17-limites-legales-techniques.md), et
comparee - jamais fusionnee - a nos propres signaux (moteur de regles +
apercu ML). Une seule ligne par actif (derniere lecture connue), comme
market_data/technical_indicators mais sans historique : Yahoo expose deja
0m/-1m/-2m/-3m de son cote, pas besoin de dupliquer cet historique ici.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domains.assets.models import Asset


class AnalystConsensus(Base):
    __tablename__ = "analyst_consensus"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    strong_buy: Mapped[int] = mapped_column(Integer, nullable=False)
    buy: Mapped[int] = mapped_column(Integer, nullable=False)
    hold: Mapped[int] = mapped_column(Integer, nullable=False)
    sell: Mapped[int] = mapped_column(Integer, nullable=False)
    strong_sell: Mapped[int] = mapped_column(Integer, nullable=False)
    consensus_score: Mapped[float] = mapped_column(Float, nullable=False)  # -2 (vente forte) a +2 (achat fort)
    consensus_label: Mapped[str] = mapped_column(String(20), nullable=False)  # 'achat' | 'neutre' | 'vente'
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    asset: Mapped[Asset] = relationship(Asset, lazy="joined")
