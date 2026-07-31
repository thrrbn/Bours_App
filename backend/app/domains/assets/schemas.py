import uuid
from datetime import date, datetime

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


class AssetStatusRead(BaseModel):
    """Fraicheur des donnees d'un actif suivi - prix, signal, consensus
    analystes - pour la page de suivi (voir assets/service.py:get_status_overview).
    Aucune de ces trois dates n'implique un rafraichissement automatique :
    voir POST /market-data/{id}/refresh, /signals/{id}/recompute,
    /analyst/{id}/refresh pour forcer une mise a jour d'un titre precis."""

    id: uuid.UUID
    ticker: str
    name: str
    market: str
    last_price_date: date | None
    last_signal_computed_at: datetime | None
    last_consensus_fetched_at: datetime | None


class CandidateAssetRead(BaseModel):
    """Suggestion de titre non suivi - factuelle (tendance Yahoo Finance,
    frequence/ton moyen des articles RSS), jamais une recommandation. Voir
    assets/discovery.py. L'utilisateur decide seul de l'ajouter (POST /assets)."""

    ticker: str
    name: str
    market_guess: str
    mention_count: int
    average_sentiment: float
