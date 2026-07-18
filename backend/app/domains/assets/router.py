import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.assets import service
from app.domains.assets.schemas import AssetCreate, AssetRead, AssetSearchResult

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


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await service.get_asset_or_raise(db, asset_id)


@router.post("", response_model=AssetRead, status_code=201)
async def create_asset(payload: AssetCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_asset(db, payload)
