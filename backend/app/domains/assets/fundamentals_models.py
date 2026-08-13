"""
Fiche titre - fondamentaux Yahoo Finance (secteur/industrie, capitalisation,
PER, rendement du dividende, fourchette 52 semaines, beta, resume
d'activite). Meme convention qu'analyst/models.py::AnalystConsensus : UNE
ligne par actif (derniere lecture connue), rafraichie a la demande - voir
fundamentals_provider.py pour la source (yfinance) et docs/17-limites-
legales-techniques.md pour les reserves sur ce type de donnee.
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domains.assets.models import Asset


class AssetFundamentals(Base):
    __tablename__ = "asset_fundamentals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    sector: Mapped[str | None] = mapped_column(String(100), index=True)
    industry: Mapped[str | None] = mapped_column(String(150))
    market_cap: Mapped[int | None] = mapped_column(BigInteger)
    trailing_pe: Mapped[float | None] = mapped_column(Float)
    forward_pe: Mapped[float | None] = mapped_column(Float)
    # Point de vigilance (voir fundamentals_provider.py) : les versions
    # recentes de yfinance renvoient deja un pourcentage (ex. 3.25 pour
    # 3.25%), pas une fraction (0.0325) - stocke tel quel, affiche avec un
    # "%" cote frontend sans transformation supplementaire.
    dividend_yield: Mapped[float | None] = mapped_column(Float)
    week52_low: Mapped[float | None] = mapped_column(Float)
    week52_high: Mapped[float | None] = mapped_column(Float)
    beta: Mapped[float | None] = mapped_column(Float)
    # 13/08/2026 : ratios complementaires (demande explicite de l'utilisateur -
    # "ameliorer enrichir les fondamentaux, ratios sectoriels, comparaison
    # peer-to-peer"). Memes reserves que les champs ci-dessus (voir
    # fundamentals_provider.py) : chacun individuellement absent frequemment
    # sur les valeurs europeennes de taille moyenne.
    return_on_equity: Mapped[float | None] = mapped_column(Float)  # ROE, en fraction (0.15 = 15%)
    debt_to_equity: Mapped[float | None] = mapped_column(Float)  # dette / capitaux propres
    profit_margin: Mapped[float | None] = mapped_column(Float)  # marge nette, en fraction
    price_to_book: Mapped[float | None] = mapped_column(Float)  # P/B
    ev_to_ebitda: Mapped[float | None] = mapped_column(Float)  # VE/EBITDA
    business_summary: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    asset: Mapped[Asset] = relationship(Asset, lazy="joined")
