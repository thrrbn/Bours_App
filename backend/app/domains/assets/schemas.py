import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

FUNDAMENTALS_DISCLAIMER = (
    "Donnees factuelles issues de Yahoo Finance (capitalisation, PER, rendement du dividende...), pas une "
    "recommandation de cette application - a interpreter avec prudence, voir /api/v1/compliance/disclaimer."
)


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


class FundamentalsRead(BaseModel):
    """Fiche titre - fondamentaux Yahoo Finance (voir fundamentals_models.py).
    Chaque champ est individuellement optionnel : frequent que Yahoo n'ait
    pas de PER/beta pour une petite valeur europeenne, voir docs/17."""

    model_config = ConfigDict(from_attributes=True)

    asset_id: uuid.UUID
    sector: str | None
    industry: str | None
    market_cap: int | None
    trailing_pe: float | None
    forward_pe: float | None
    dividend_yield: float | None
    week52_low: float | None
    week52_high: float | None
    beta: float | None
    business_summary: str | None
    fetched_at: datetime
    source: str = "yahoo_finance"
    disclaimer: str = FUNDAMENTALS_DISCLAIMER


class SectorPeerAverage(BaseModel):
    """Moyenne calculee sur les AUTRES actifs suivis du meme secteur dont les
    fondamentaux ont deja ete rafraichis - pas un appel Yahoo Finance
    supplementaire (voir fundamentals_repository.py::list_by_sector)."""

    sector: str
    peer_count: int
    avg_trailing_pe: float | None
    avg_dividend_yield: float | None
    avg_market_cap: float | None


class SectorComparisonRead(BaseModel):
    asset: AssetRead
    this_trailing_pe: float | None
    this_dividend_yield: float | None
    this_market_cap: int | None
    peers: SectorPeerAverage | None
    note: str


class AssetLookupRead(BaseModel):
    """Apercu live d'un ticker Yahoo Finance, suivi ou non - voir
    service.py::lookup_ticker. Si `already_tracked_id` est renseigne, le
    titre existe deja en base (pas besoin de POST /assets)."""

    ticker: str
    name: str | None
    market_guess: str
    currency: str | None
    sector: str | None
    industry: str | None
    last_price: float | None
    market_cap: int | None
    already_tracked_id: uuid.UUID | None = None


class CandidateAssetRead(BaseModel):
    """Suggestion de titre non suivi - factuelle (tendance Yahoo Finance,
    frequence/ton moyen des articles RSS), jamais une recommandation. Voir
    assets/discovery.py. L'utilisateur decide seul de l'ajouter (POST /assets)."""

    ticker: str
    name: str
    market_guess: str
    mention_count: int
    average_sentiment: float
