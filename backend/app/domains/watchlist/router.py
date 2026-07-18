import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.watchlist import service
from app.domains.watchlist.schemas import WatchlistItemCreate, WatchlistItemRead
from app.domains.watchlist.service import AlreadyInWatchlistError, NotInWatchlistError

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItemRead])
async def list_watchlist(db: AsyncSession = Depends(get_db)):
    return await service.list_watchlist(db)


@router.post("", response_model=WatchlistItemRead, status_code=201)
async def add_to_watchlist(payload: WatchlistItemCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await service.add_to_watchlist(db, payload.asset_id, payload.notify_on_change)
    except AlreadyInWatchlistError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{asset_id}", status_code=204)
async def remove_from_watchlist(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        await service.remove_from_watchlist(db, asset_id)
    except NotInWatchlistError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
