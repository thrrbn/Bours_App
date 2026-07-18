"""Acces aux donnees du portefeuille virtuel - requetes SQL/ORM pures."""
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.portfolio.models import PortfolioPosition, PortfolioState, PortfolioTransaction


async def get_state(db: AsyncSession) -> PortfolioState | None:
    result = await db.execute(select(PortfolioState).limit(1))
    return result.scalar_one_or_none()


async def create_state(db: AsyncSession, starting_cash: float) -> PortfolioState:
    state = PortfolioState(cash_balance=starting_cash, starting_cash=starting_cash)
    db.add(state)
    await db.commit()
    await db.refresh(state)
    return state


async def update_cash_balance(db: AsyncSession, state: PortfolioState, new_balance: float) -> None:
    state.cash_balance = new_balance
    await db.commit()


async def list_positions(db: AsyncSession) -> list[PortfolioPosition]:
    stmt = select(PortfolioPosition).options(selectinload(PortfolioPosition.asset))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_position(db: AsyncSession, asset_id: uuid.UUID) -> PortfolioPosition | None:
    stmt = select(PortfolioPosition).where(PortfolioPosition.asset_id == asset_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_position(db: AsyncSession, asset_id: uuid.UUID, quantity: float, avg_cost: float) -> None:
    existing = await get_position(db, asset_id)
    if existing is None:
        db.add(PortfolioPosition(asset_id=asset_id, quantity=quantity, avg_cost=avg_cost))
    else:
        existing.quantity = quantity
        existing.avg_cost = avg_cost
    await db.commit()


async def delete_position(db: AsyncSession, position: PortfolioPosition) -> None:
    await db.delete(position)
    await db.commit()


async def add_transaction(
    db: AsyncSession,
    asset_id: uuid.UUID,
    side: str,
    quantity: float,
    price: float,
    total_amount: float,
    realized_pnl: float | None,
    price_date,
) -> PortfolioTransaction:
    transaction = PortfolioTransaction(
        asset_id=asset_id,
        side=side,
        quantity=quantity,
        price=price,
        total_amount=total_amount,
        realized_pnl=realized_pnl,
        price_date=price_date,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction, attribute_names=["asset"])
    return transaction


async def list_transactions(db: AsyncSession, limit: int = 100) -> list[PortfolioTransaction]:
    stmt = (
        select(PortfolioTransaction)
        .options(selectinload(PortfolioTransaction.asset))
        .order_by(PortfolioTransaction.executed_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def reset_all(db: AsyncSession, starting_cash: float) -> PortfolioState:
    await db.execute(delete(PortfolioTransaction))
    await db.execute(delete(PortfolioPosition))
    await db.execute(delete(PortfolioState))
    await db.commit()
    return await create_state(db, starting_cash)
