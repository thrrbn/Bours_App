"""
Modele ORM du bac a sable pedagogique (31/07/2026, Phase 3 - voir
docs/STACK.md). Delibirement dans un fichier separe de `models.py` : dans ce
domaine, `models.py` designe deja les fonctions d'entrainement/prediction
(Random Forest, XGBoost, ARIMA, Prophet, ensemble - Phases 1/2), pas des
modeles SQLAlchemy - une exception assumee a la convention du reste du projet
(`models.py` = ORM dans tous les autres domaines) pour eviter de renommer un
module deja largement importe. `db_models.py` porte donc l'unique table
propre a ce domaine.

`TrainingJob` casse (a dessein, dans ce seul domaine) le principe "aucune
ecriture" qui prevalait jusqu'ici pour analysis_lab (voir feature_engineering.py/
models.py/service.py) : les modeles sequentiels (LSTM/GRU/Transformer, Phase 3)
prennent plusieurs secondes a s'entrainer, trop long pour un appel HTTP
synchrone (GET /compare, comme pour Random Forest/XGBoost/ARIMA/Prophet) -
il faut donc un job asynchrone dont le statut/resultat doit bien etre
persiste quelque part pour etre interroge (polling) apres coup. Portee
strictement limitee a CE domaine : ne touche jamais `signals`/`portfolio`/
`backtest_results` - uniquement le suivi de ses propres entrainements
pedagogiques.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    model_name: Mapped[str] = mapped_column(String(30), nullable=False)  # 'lstm' (Phase 3 - gru/transformer a venir)
    horizon: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_PENDING)
    # Resultat serialise (ModelResult-like : predicted_direction, probability_up,
    # train_accuracy, validation_accuracy, explanation...) une fois status='completed'.
    result: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
