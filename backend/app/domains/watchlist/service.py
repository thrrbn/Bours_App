"""Orchestration watchlist : validation metier + delegation au repository."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AssetNotFoundError
from app.domains.assets import repository as assets_repository
from app.domains.watchlist import repository
from app.domains.watchlist.models import WatchlistItem


class AlreadyInWatchlistError(Exception):
    def __init__(self, asset_id: uuid.UUID):
        self.asset_id = asset_id
        super().__init__(f"Actif deja dans la watchlist: {asset_id}")


class NotInWatchlistError(Exception):
    def __init__(self, asset_id: uuid.UUID):
        self.asset_id = asset_id
        super().__init__(f"Actif absent de la watchlist: {asset_id}")


async def list_watchlist(db: AsyncSession) -> list[WatchlistItem]:
    return await repository.list_all(db)


async def add_to_watchlist(db: AsyncSession, asset_id: uuid.UUID, notify_on_change: bool) -> WatchlistItem:
    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))

    existing = await repository.get_by_asset_id(db, asset_id)
    if existing is not None:
        raise AlreadyInWatchlistError(asset_id)

    return await repository.add(db, asset_id, notify_on_change)


async def remove_from_watchlist(db: AsyncSession, asset_id: uuid.UUID) -> None:
    existing = await repository.get_by_asset_id(db, asset_id)
    if existing is None:
        raise NotInWatchlistError(asset_id)
    await repository.remove(db, existing)
