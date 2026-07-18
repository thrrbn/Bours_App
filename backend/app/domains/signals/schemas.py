from datetime import datetime

from pydantic import BaseModel, field_validator


class ScoreSet(BaseModel):
    technical: float
    news: float
    risk: float
    confidence: float


class ExplanationRead(BaseModel):
    component: str
    contribution_pct: float
    text: str
    supporting_data: dict | None = None


class MLPreviewRead(BaseModel):
    """
    Apercu du modele statistique V2 (regression logistique), affiche a cote
    du signal officiel (moteur de regles) sans jamais le remplacer tant que
    la superiorite du modele n'est pas prouvee par backtesting (docs/11).

    `model_status` == 'en_apprentissage' : a afficher avec une couleur
    d'avertissement cote frontend (donnees d'entrainement insuffisantes).
    `model_status` == 'fiable' : seuil minimal d'exemples atteint.
    """

    engine_version: str
    model_status: str
    sample_count: int
    min_required_samples: int
    probability_up: float | None
    final_signal: str | None
    explanation: str


class SignalRead(BaseModel):
    horizon: str
    computed_at: datetime
    scores: ScoreSet
    final_signal: str
    engine_version: str
    explanations: list[ExplanationRead]
    ml_preview: MLPreviewRead | None = None
    disclaimer: str = (
        "Ce signal est un score statistique, pas un conseil en investissement. "
        "Voir /api/v1/compliance/disclaimer."
    )

    @field_validator("explanations")
    @classmethod
    def explanations_must_not_be_empty(cls, value: list[ExplanationRead]) -> list[ExplanationRead]:
        if not value:
            raise ValueError("Un signal ne peut jamais etre renvoye sans explication.")
        return value
