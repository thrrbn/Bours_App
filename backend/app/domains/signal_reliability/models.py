import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SignalOutcome(Base):
    """
    Scorecard de fiabilite reelle (13/08/2026, demande explicite de
    l'utilisateur : "un vrai score card de fiabilite historique du moteur de
    regles", distinct du backtest a la demande - voir domaine backtests).
    Une ligne = UN signal reel deja calcule (table signals), evalue UNE SEULE
    FOIS une fois son horizon ecoule (voir jobs/evaluate_signal_outcomes_job.py),
    avec le rendement reellement observe ensuite et si la direction du signal
    etait correcte. Alimente en continu (job quotidien), contrairement au
    backtest a la demande qui rejoue tout a chaque fois.

    signal_id UNIQUE : garantit qu'un signal n'est jamais evalue deux fois
    (idempotence du job - simple filtre "signal_id NOT IN (deja evalues)").
    """

    __tablename__ = "signal_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("signals.id", ondelete="CASCADE"), unique=True, index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    horizon: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # Copie de signals.computed_at (denormalisation volontaire) : evite un
    # JOIN sur signals pour chaque requete de fenetre glissante (30/90/365
    # jours) du scorecard - lu tres frequemment, ecrit une seule fois.
    signal_computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    final_signal: Mapped[str] = mapped_column(String(30), nullable=False)
    # Rendement reellement observe entre le signal et la fin de son horizon
    # (meme convention que backtests/service.py::_compute_forward_return -
    # positif = hausse). Duplique volontairement (isolation des domaines,
    # meme convention que backtests/service.py::HORIZON_FORWARD_DAYS).
    forward_return: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    # True si la direction du signal correspondait au sens du rendement
    # observe (achat_speculatif/surveillance corrects si forward_return > 0,
    # prudence/vente_defensive corrects si forward_return <= 0) - "neutre"
    # n'est jamais evalue (exclu en amont par le job, voir evaluate_signals()
    # dans backtests/service.py pour la meme regle).
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
