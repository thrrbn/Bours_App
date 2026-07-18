import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.analyst import service
from app.domains.analyst.schemas import AnalystConsensusRead, ComparisonRead, PortfolioAlertRead

router = APIRouter(prefix="/api/v1/analyst", tags=["analyst"])


@router.post("/{asset_id}/refresh", response_model=AnalystConsensusRead | None)
async def refresh_consensus(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await service.refresh_for_asset(db, asset_id)


@router.post("/refresh-all")
async def refresh_all(db: AsyncSession = Depends(get_db)):
    return await service.refresh_all(db)


@router.get("/top-buys", response_model=list[AnalystConsensusRead])
async def top_buys(limit: int = Query(10, ge=1, le=20), db: AsyncSession = Depends(get_db)):
    return await service.get_top_buys(db, limit)


@router.get("/portfolio-alerts", response_model=list[PortfolioAlertRead])
async def portfolio_alerts(db: AsyncSession = Depends(get_db)):
    return await service.get_portfolio_alerts(db)


@router.get("/comparison-table", response_model=list[ComparisonRead])
async def comparison_table(
    horizon: str = Query("medium", pattern="^(short|medium|long)$"),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_comparison_table(db, horizon)


@router.get("/{asset_id}/comparison", response_model=ComparisonRead)
async def comparison(
    asset_id: uuid.UUID,
    horizon: str = Query("medium", pattern="^(short|medium|long)$"),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_comparison(db, asset_id, horizon)
