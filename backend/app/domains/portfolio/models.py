"""
Portefeuille virtuel de simulation (Etape 12) : aucun lien avec un compte de
courtage reel, purement pedagogique. Mono-portefeuille (comme la watchlist,
voir watchlist/models.py) - une seule ligne PortfolioState fait office de
singleton, cree a la premiere utilisation avec le cash de depart configure
(settings.portfolio_starting_cash).
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func, text
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
    # 31/07/2026 : derniere date de detachement de dividende deja creditee
    # pour cette position (voir jobs/credit_dividends_job.py) - initialisee a
    # la date du premier achat (pas de retro-credit de dividendes anterieurs a
    # l'ouverture de la position, on ne detenait pas les actions a ce moment-la).
    # Simplification assumee : un rachat ulterieur (renforcement de position)
    # ne cree pas de "lot" distinct - le prochain dividende credite utilisera
    # la quantite TOTALE detenue au moment du job, meme pour les actions
    # ajoutees apres le dernier dividende. Ecart mineur pour un outil
    # pedagogique, pas une comptabilite de courtier reelle.
    dividends_credited_until: Mapped[date | None] = mapped_column(Date)
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
    # 31/07/2026 : 'dividend' ajoute a 'buy'/'sell' (voir jobs/credit_dividends_job.py) -
    # une ligne 'dividend' represente un versement credite au cash, pas un ordre.
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # 'buy' | 'sell' | 'dividend'
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    # price = prix REELLEMENT execute (apres slippage) ; quoted_price = cours
    # brut avant slippage, conserve pour transparence (Etape 17).
    price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    quoted_price: Mapped[float | None] = mapped_column(Numeric(18, 6))
    commission: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    slippage_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    # 31/07/2026 : taxe belge sur les operations de bourse (TOB/beurstaks),
    # tracee separement de la commission/du slippage pour un detail de cout
    # transparent (objectif pedagogique, voir docs/STACK.md) - 0 pour les
    # actifs BINANCE (non applicable) et pour les lignes 'dividend' (le
    # precompte mobilier sur dividende est deja deduit du montant credite, pas
    # ajoute en frais separes - voir jobs/credit_dividends_job.py).
    tob_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    realized_pnl: Mapped[float | None] = mapped_column(Numeric(18, 2))
    price_date: Mapped[date] = mapped_column(nullable=False)  # date du dernier cours utilise, pas la date d'execution
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped[Asset] = relationship(Asset, lazy="joined")
