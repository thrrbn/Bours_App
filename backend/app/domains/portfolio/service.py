"""
Orchestration du portefeuille virtuel : execution des achats/ventes au
DERNIER COURS CONNU (pas de choix de date passee - decision produit du
18/07/2026, la simulation "a partir de maintenant" suffit et evite la
complexite d'une UI de selection de date). Aucune connexion a un vrai compte
de courtage : tout est simule en base (voir models.py).
"""
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AssetNotFoundError, InsufficientDataError
from app.domains.assets import repository as assets_repository
from app.domains.market_data import repository as market_data_repository
from app.domains.portfolio import repository
from app.domains.portfolio.models import PortfolioPosition, PortfolioState, PortfolioTransaction
from app.domains.portfolio.schemas import PortfolioSummaryRead, PositionRead, TransactionRead


class InsufficientFundsError(Exception):
    def __init__(self, needed: float, available: float):
        self.needed = needed
        self.available = available
        super().__init__(f"Fonds insuffisants: {needed:.2f} EUR necessaires, {available:.2f} EUR disponibles.")


class InsufficientPositionError(Exception):
    def __init__(self, asset_id: uuid.UUID, requested: float, held: float):
        self.asset_id = asset_id
        super().__init__(f"Position insuffisante: {requested} demande(s), {held} detenue(s).")


async def _get_or_create_state(db: AsyncSession) -> PortfolioState:
    state = await repository.get_state(db)
    if state is None:
        settings = get_settings()
        state = await repository.create_state(db, settings.portfolio_starting_cash)
    return state


async def _get_latest_price(db: AsyncSession, asset_id: uuid.UUID) -> tuple[float, date]:
    bar = await market_data_repository.get_latest_bar(db, asset_id)
    if bar is None:
        raise InsufficientDataError(
            "Aucun cours connu pour cet actif - lance d'abord un rafraichissement des prix "
            "(POST /api/v1/market-data/{asset_id}/refresh)."
        )
    return float(bar.close), bar.trade_date


async def buy(db: AsyncSession, asset_id: uuid.UUID, quantity: float) -> TransactionRead:
    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))

    state = await _get_or_create_state(db)
    price, price_date = await _get_latest_price(db, asset_id)
    total_cost = round(price * quantity, 2)

    if total_cost > float(state.cash_balance):
        raise InsufficientFundsError(total_cost, float(state.cash_balance))

    existing = await repository.get_position(db, asset_id)
    if existing is None:
        new_quantity = quantity
        new_avg_cost = price
    else:
        old_quantity = float(existing.quantity)
        old_avg_cost = float(existing.avg_cost)
        new_quantity = old_quantity + quantity
        new_avg_cost = ((old_quantity * old_avg_cost) + (quantity * price)) / new_quantity

    await repository.upsert_position(db, asset_id, new_quantity, new_avg_cost)
    await repository.update_cash_balance(db, state, float(state.cash_balance) - total_cost)

    transaction = await repository.add_transaction(
        db, asset_id, "buy", quantity, price, total_cost, realized_pnl=None, price_date=price_date
    )
    return TransactionRead.model_validate(transaction)


async def sell(db: AsyncSession, asset_id: uuid.UUID, quantity: float) -> TransactionRead:
    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))

    state = await _get_or_create_state(db)
    position = await repository.get_position(db, asset_id)
    held = float(position.quantity) if position else 0.0
    if position is None or quantity > held:
        raise InsufficientPositionError(asset_id, quantity, held)

    price, price_date = await _get_latest_price(db, asset_id)
    proceeds = round(price * quantity, 2)
    realized_pnl = round((price - float(position.avg_cost)) * quantity, 2)

    remaining_quantity = held - quantity
    if remaining_quantity <= 0:
        await repository.delete_position(db, position)
    else:
        await repository.upsert_position(db, asset_id, remaining_quantity, float(position.avg_cost))

    await repository.update_cash_balance(db, state, float(state.cash_balance) + proceeds)

    transaction = await repository.add_transaction(
        db, asset_id, "sell", quantity, price, proceeds, realized_pnl=realized_pnl, price_date=price_date
    )
    return TransactionRead.model_validate(transaction)


async def get_summary(db: AsyncSession) -> PortfolioSummaryRead:
    state = await _get_or_create_state(db)
    positions = await repository.list_positions(db)

    position_reads: list[PositionRead] = []
    positions_value = 0.0

    for position in positions:
        bar = await market_data_repository.get_latest_bar(db, position.asset_id)
        current_price = float(bar.close) if bar else None
        quantity = float(position.quantity)
        avg_cost = float(position.avg_cost)

        market_value = current_price * quantity if current_price is not None else None
        unrealized_pnl = (current_price - avg_cost) * quantity if current_price is not None else None
        unrealized_pnl_pct = (
            ((current_price - avg_cost) / avg_cost * 100) if current_price is not None and avg_cost > 0 else None
        )

        if market_value is not None:
            positions_value += market_value

        position_reads.append(
            PositionRead(
                asset=position.asset,
                quantity=quantity,
                avg_cost=avg_cost,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
            )
        )

    cash_balance = float(state.cash_balance)
    starting_cash = float(state.starting_cash)
    total_value = cash_balance + positions_value
    total_pnl = total_value - starting_cash
    total_pnl_pct = (total_pnl / starting_cash * 100) if starting_cash > 0 else 0.0

    return PortfolioSummaryRead(
        cash_balance=cash_balance,
        starting_cash=starting_cash,
        positions_value=positions_value,
        total_value=total_value,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        positions=position_reads,
    )


async def get_transactions(db: AsyncSession) -> list[TransactionRead]:
    transactions = await repository.list_transactions(db)
    return [TransactionRead.model_validate(t) for t in transactions]


async def reset_portfolio(db: AsyncSession) -> PortfolioSummaryRead:
    settings = get_settings()
    await repository.reset_all(db, settings.portfolio_starting_cash)
    return await get_summary(db)
