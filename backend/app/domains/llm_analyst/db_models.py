"""
Modele ORM du domaine llm_analyst (16/08/2026, voir docs/20-instance-locale-pc-mac.md).

`AnalysisJob` suit exactement le meme pattern que `TrainingJob`
(analysis_lab/db_models.py, Phase 3) : un appel a un modele local (ici
Ollama, plutot qu'un entrainement LSTM) prend de quelques secondes a
plusieurs minutes - trop long pour un appel HTTP synchrone, d'ou un job
asynchrone dont le statut/resultat est persiste ici pour etre interroge
(polling) apres coup.

Cette table existe dans le MEME schema que le reste de l'application (donc
aussi dans la migration jouee sur le NAS) mais ne sera jamais alimentee
la-bas : la feature est desactivee par defaut (settings.enable_llm_analyst),
voir router.py::require_enabled. Une table vide sur le NAS n'a aucun cout
reel."""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class AnalysisJob(Base):
    __tablename__ = "llm_analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    strategy_name: Mapped[str] = mapped_column(String(30), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_PENDING)
    # Resultat serialise : markdown, llm_data, citation_warnings, from_cache,
    # low_sample_warning - voir schemas.py::AnalysisJobRead et
    # jobs/llm_analysis_job.py pour la construction exacte.
    result: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
