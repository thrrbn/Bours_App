"""Job de calcul des signaux - reutilise le service signals pour les 3 horizons."""
import logging

from app.database import AsyncSessionLocal
from app.domains.assets.repository import list_all as list_all_assets
from app.domains.signals.service import compute_signal_for_asset
from app.domains.signals.training import build_training_set

logger = logging.getLogger(__name__)
HORIZONS = ("short", "medium", "long")


async def compute_signals_job() -> dict:
    async with AsyncSessionLocal() as db:
        assets = await list_all_assets(db)
        # Construit le jeu d'entrainement ML UNE SEULE FOIS pour tout le job,
        # au lieu d'une fois par (actif x horizon) - meme bug de performance
        # que get_comparison_table (voir analyst/service.py), corrige le
        # 30/07/2026. Sans ca : nb_actifs x 3 horizons x reconstructions
        # completes du jeu d'entrainement, devenu impraticable depuis
        # l'elargissement de l'univers d'actifs (~189 actifs possibles).
        training_examples = await build_training_set(db)
        errors = 0
        for asset in assets:
            for horizon in HORIZONS:
                try:
                    await compute_signal_for_asset(db, asset.id, horizon, training_examples=training_examples)
                except Exception:
                    errors += 1
                    logger.exception("Echec calcul signal %s/%s", asset.ticker, horizon)
        logger.info(
            "compute_signals_job termine: %s actifs x %s horizons, %s erreurs", len(assets), len(HORIZONS), errors
        )
        return {"total_assets": len(assets), "horizons": len(HORIZONS), "errors": errors}
