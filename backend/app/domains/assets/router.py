import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.assets import service
from app.domains.assets.schemas import (
    AssetCreate,
    AssetLookupRead,
    AssetRead,
    AssetSearchResult,
    AssetStatusRead,
    CandidateAssetRead,
    FundamentalsRead,
    SectorComparisonRead,
)

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
async def list_assets(
    market: str | None = None,
    sector: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await service.list_assets(db, market, sector)


@router.get("/search", response_model=list[AssetSearchResult])
async def search_assets(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    return await service.search_assets(db, q)


@router.get("/status", response_model=list[AssetStatusRead])
async def get_status_overview(db: AsyncSession = Depends(get_db)):
    """
    Fraicheur des donnees (prix/signal/consensus) pour tous les actifs
    suivis - alimente la page de suivi des actifs (rafraichissement titre
    par titre). Route declaree avant /{asset_id} pour eviter que FastAPI
    n'essaie de parser "status" comme un UUID.
    """
    return await service.get_status_overview(db)


@router.get("/discover-candidates", response_model=list[CandidateAssetRead])
async def discover_candidates(limit: int = Query(default=10, ge=1, le=25), db: AsyncSession = Depends(get_db)):
    """
    Suggestions de titres non suivis (tendances Yahoo Finance + sentiment RSS
    recent, voir assets/discovery.py) - purement informatif, AUCUN ajout
    automatique. Route declaree avant /{asset_id} pour eviter que FastAPI
    n'essaie de parser "discover-candidates" comme un UUID.
    """
    return await service.discover_candidates(db, limit=limit)


@router.get("/lookup", response_model=AssetLookupRead)
async def lookup_ticker(ticker: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    """
    Recherche live sur Yahoo Finance d'un ticker - PAS limite aux actifs deja
    suivis (contrairement a GET /assets/search) : c'est le point d'entree du
    flux "ajouter un titre absent de la liste" (voir service.py::lookup_ticker).
    Route declaree avant /{asset_id} pour eviter que FastAPI n'essaie de
    parser "lookup" comme un UUID.
    """
    return await service.lookup_ticker(db, ticker)


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await service.get_asset_or_raise(db, asset_id)


@router.get("/{asset_id}/fundamentals", response_model=FundamentalsRead | None)
async def get_fundamentals(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Derniere fiche fondamentaux connue pour ce titre - None si jamais
    rafraichie (voir POST .../fundamentals/refresh), pas une erreur."""
    return await service.get_fundamentals(db, asset_id)


@router.post("/{asset_id}/fundamentals/refresh", response_model=FundamentalsRead)
async def refresh_fundamentals(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await service.refresh_fundamentals(db, asset_id)


@router.get("/{asset_id}/fundamentals/sector-comparison", response_model=SectorComparisonRead)
async def sector_comparison(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await service.get_sector_comparison(db, asset_id)


@router.post("", response_model=AssetRead, status_code=201)
async def create_asset(payload: AssetCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_asset(db, payload)


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Retire un actif de la liste (desactivation, pas une suppression physique
    - voir service.py::delete_asset) : disparait de GET /assets et
    /assets/search, n'est plus traite par les jobs planifies. 409 si encore
    detenu en portefeuille virtuel.
    """
    await service.delete_asset(db, asset_id)
