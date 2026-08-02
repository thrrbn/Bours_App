from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MarketSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    captured_at: datetime
    # Listes/dicts JSONB renvoyees telles quelles (voir models.py) - forme
    # deja stable cote provider/service, pas de sous-modele dedie pour
    # rester simple (meme choix que analysis_lab pour TrainingJob.result).
    indices: list[dict]
    movers: dict
