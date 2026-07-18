import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.assets.schemas import AssetRead


class WatchlistItemCreate(BaseModel):
    asset_id: uuid.UUID
    notify_on_change: bool = True


class WatchlistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset: AssetRead
    notify_on_change: bool
    added_at: datetime
