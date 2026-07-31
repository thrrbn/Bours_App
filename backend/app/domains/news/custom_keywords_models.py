"""
Mots-cles personnalises (31/07/2026) - complement au lexique fixe
(nlp/lexicon.py) : l'utilisateur peut suivre ses propres termes/opportunites
(ex. nom d'un concurrent, "rappel produit", "OPA") sans toucher au code.
Liste GLOBALE (appliquee a tous les actifs suivis, pas de portee par titre -
plus simple a gerer, voir discussion avec l'utilisateur le 31/07/2026),
fusionnee au lexique fixe au moment de l'ingestion (voir service.py::
ingest_and_score) et de la synthese du briefing quotidien (voir
notifications/briefing_service.py).

`weight` est optionnel (defaut 0.0 = n'influence pas le score de sentiment,
sert uniquement a FLAGUER la presence du terme) - laisse a l'utilisateur la
possibilite d'assigner un poids (-1 a 1) s'il veut que ce mot-cle compte aussi
dans le calcul du sentiment, comme le lexique fixe.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CustomKeyword(Base):
    __tablename__ = "custom_keywords"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    horizon_impact: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
