"""
Job quotidien de credit des dividendes au portefeuille virtuel (31/07/2026) -
voir docs/STACK.md pour le recit complet du gap identifie (le portefeuille
n'achete/vend qu'au cours brut, sans jamais recevoir le cash reel verse par
une action a un detenteur au jour du detachement, ce qui sous-estimait le
rendement total simule pour les titres a dividende).

Pour chaque position ouverte, on cherche les dividendes detaches depuis
`dividends_credited_until` (voir portfolio/models.py::PortfolioPosition) et on
credite le montant NET (apres precompte mobilier simule, voir
config.py::portfolio_dividend_withholding_pct) au cash_balance, avec une
transaction 'dividend' pour tracabilite.

Simplification assumee (documentee sur le modele) : on utilise la quantite
TOTALE detenue au moment ou ce job tourne, pas la quantite exacte detenue au
jour precis du detachement - un rachat/une vente entre l'ex-date et
l'execution quotidienne du job introduit un ecart mineur, acceptable pour un
outil pedagogique (pas une comptabilite de courtier reelle).
"""
import logging

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.domains.market_data import repository as market_data_repository
from app.domains.portfolio import repository as portfolio_repository

logger = logging.getLogger(__name__)


def _net_dividend_amount(quantity_held: float, amount_per_share: float, withholding_pct: float) -> float:
    """
    Fonction pure (testable sans DB) : montant NET credite au cash_balance
    pour un dividende donne, apres precompte mobilier simule (voir
    config.py::portfolio_dividend_withholding_pct).
    """
    gross_amount = quantity_held * amount_per_share
    return round(gross_amount * (1 - withholding_pct), 2)


async def credit_dividends_job() -> dict:
    async with AsyncSessionLocal() as db:
        settings = get_settings()
        positions = await portfolio_repository.list_positions(db)
        dividends_credited = 0
        total_credited = 0.0
        errors = 0

        for position in positions:
            try:
                since = position.dividends_credited_until
                if since is None:
                    # Ne devrait plus arriver (upsert_position initialise ce
                    # champ depuis le 31/07/2026), mais garde-fou pour une
                    # position creee avant ce correctif : ne rien crediter
                    # retroactivement plutot que deviner une date de reference.
                    continue

                dividends = await market_data_repository.get_dividends_after(db, position.asset_id, since)
                if not dividends:
                    continue

                quantity_held = float(position.quantity)
                state = await portfolio_repository.get_state(db)
                for dividend in dividends:
                    net_amount = _net_dividend_amount(
                        quantity_held, float(dividend.amount_per_share), settings.portfolio_dividend_withholding_pct
                    )
                    if net_amount <= 0:
                        continue
                    await portfolio_repository.update_cash_balance(db, state, float(state.cash_balance) + net_amount)
                    await portfolio_repository.add_transaction(
                        db,
                        position.asset_id,
                        "dividend",
                        quantity_held,
                        float(dividend.amount_per_share),
                        net_amount,
                        realized_pnl=None,
                        price_date=dividend.ex_date,
                    )
                    dividends_credited += 1
                    total_credited += net_amount

                await portfolio_repository.update_dividends_credited_until(db, position, dividends[-1].ex_date)
            except Exception:
                errors += 1
                logger.exception("Echec credit dividendes pour la position asset_id=%s", position.asset_id)

        logger.info(
            "credit_dividends_job termine: %s dividendes credites (%.2f EUR net), %s erreurs",
            dividends_credited,
            total_credited,
            errors,
        )
        return {"dividends_credited": dividends_credited, "total_credited": round(total_credited, 2), "errors": errors}
