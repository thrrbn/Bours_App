import uuid

from pydantic import BaseModel, ConfigDict


class AssetBase(BaseModel):
    ticker: str
    name: str
    market: str
    sector: str | None = None
    currency: str
    isin: str | None = None


class AssetCreate(AssetBase):
    pass


class AssetRead(AssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool


class AssetSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticker: str
    name: str
    market: str
