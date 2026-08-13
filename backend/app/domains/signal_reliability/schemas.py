from datetime import datetime

from pydantic import BaseModel

DISCLAIMER = (
    "Mesure la fiabilite historique du moteur de signal REEL sur les signaux deja calcules - jamais une "
    "prediction ni une garantie sur l'avenir. Un signal 'neutre' n'est jamais evalue (aucune direction a juger)."
)


class WindowStats(BaseModel):
    count: int
    precision: float | None


class ScorecardRead(BaseModel):
    """
    horizons : {horizon: {window_key: WindowStats}} - window_key parmi
    '30d'/'90d'/'365d'/'all' (voir repository.py::SCORECARD_WINDOWS). Pas de
    schema intermediaire par horizon : correspond directement a la forme
    retournee par service.py::get_scorecard.
    """

    horizons: dict[str, dict[str, WindowStats]]
    last_evaluated_at: datetime | None
    disclaimer: str = DISCLAIMER
