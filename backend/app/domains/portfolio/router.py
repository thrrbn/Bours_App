from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.portfolio import service
from app.domains.portfolio.schemas import BuyRequest, PortfolioSummaryRead, SellRequest, TransactionRead
from app.domains.portfolio.service import InsufficientFundsError, InsufficientPositionError

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioSummaryRead)
async def get_portfolio(db: AsyncSession = Depends(get_db)):
    return await service.get_summary(db)


@router.post("/buy", response_model=TransactionRead, status_code=201)
async def buy(payload: BuyRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await service.buy(db, payload.asset_id, payload.quantity)
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/sell", response_model=TransactionRead, status_code=201)
async def sell(payload: SellRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await service.sell(db, payload.asset_id, payload.quantity)
    except InsufficientPositionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/transactions", response_model=list[TransactionRead])
async def list_transactions(db: AsyncSession = Depends(get_db)):
    return await service.get_transactions(db)


@router.post("/reset", response_model=PortfolioSummaryRead)
async def reset_portfolio(db: AsyncSession = Depends(get_db)):
    return await service.reset_portfolio(db)
