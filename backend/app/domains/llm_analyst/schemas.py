"""Schemas Pydantic du domaine llm_analyst (16/08/2026)."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel

DISCLAIMER = (
    "Rapport genere par un LLM local (Ollama) a partir de faits precalcules en Python pur, jamais decouverts "
    "par le modele lui-meme. Ne constitue en aucun cas un conseil en investissement ni une prediction - un "
    "backtest passe ne garantit rien sur l'avenir. Feature reservee a l'instance locale PC/Mac, voir "
    "docs/20-instance-locale-pc-mac.md."
)


class AnalysisStatusRead(BaseModel):
    """Reponse de GET /llm-analyst/status - permet au frontend de savoir s'il
    doit afficher le lien de navigation vers cette page, sans dependre d'un
    flag de build (voir docs/20 : le meme frontend buildé peut pointer vers
    une instance NAS (enabled=false) ou une instance locale (enabled=true),
    la decision est prise a l'execution, pas a la compilation)."""

    enabled: bool
    ollama_model: str


class AnalysisJobCreate(BaseModel):
    asset_id: uuid.UUID
    strategy_name: str
    period_start: date
    period_end: date
    model_name: str | None = None  # None = utilise settings.ollama_model


class AnalysisJobRead(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    strategy_name: str
    period_start: date
    period_end: date
    model_name: str
    status: str  # 'pending' | 'running' | 'completed' | 'failed'
    result: dict | None = None  # {markdown, citation_warnings, low_sample_warning, from_cache} une fois 'completed'
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    disclaimer: str = DISCLAIMER
