"""
Scorecard de fiabilite reelle des signaux (13/08/2026, demande explicite de
l'utilisateur : "un vrai score card de fiabilite historique du moteur de
regles / pas juste du backtest"). Complementaire du domaine backtests (rejeu
A LA DEMANDE, sur une periode choisie) : ici, chaque signal reel calcule par
le moteur de production est evalue UNE SEULE FOIS, automatiquement, des que
son horizon est ecoule - voir jobs/evaluate_signal_outcomes_job.py pour
l'orchestration quotidienne, repository.py pour le stockage/l'agregation.

Meme regle de succes que backtests/service.py::evaluate_signals() (duplique
volontairement - isolation des domaines, voir docstring de ce module) : un
signal 'achat_speculatif'/'surveillance' est correct si le rendement observe
ensuite est positif, 'prudence'/'vente_defensive' correct si negatif ou nul.
'neutre' n'est jamais evalue.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_data.models import PriceBar
from app.domains.signal_reliability import repository

logger = logging.getLogger(__name__)

# Duplique volontairement backtests/service.py::HORIZON_FORWARD_DAYS et
# signals/training.py::HORIZON_FORWARD_DAYS (isolation des domaines, meme
# convention deja etablie ailleurs dans ce projet).
HORIZON_FORWARD_DAYS = {"short": 5, "medium": 20, "long": 60}
HORIZONS = ("short", "medium", "long")

_BULLISH_SIGNALS = ("achat_speculatif", "surveillance")

# Marge generose (jours CALENDAIRES) avant de considerer un signal comme
# "probablement mur" et de tenter son evaluation - HORIZON_FORWARD_DAYS est
# en jours de BOURSE (week-ends/feries exclus), x2 + 5 couvre largement
# l'ecart avec les jours calendaires. La maturite REELLE est ensuite verifiee
# par le nombre de barres de prix effectivement disponibles (voir
# _evaluate_horizon ci-dessous) - cette marge n'est qu'un filtre de
# performance pour eviter d'interroger des signaux manifestement trop recents.
_CANDIDATE_MARGIN_DAYS = 5


def _return_price(bar: PriceBar) -> float:
    """Duplique de backtests/service.py::_return_price (isolation des
    domaines) - cours ajuste des dividendes/splits, repli sur le brut."""
    return float(bar.adjusted_close) if bar.adjusted_close is not None else float(bar.close)


def _is_correct(final_signal: str, forward_return: float) -> bool:
    bullish = final_signal in _BULLISH_SIGNALS
    return (forward_return > 0) == bullish


async def _evaluate_horizon(db: AsyncSession, horizon: str) -> tuple[int, int]:
    """Retourne (nb_evalues, nb_signaux_candidats) pour cet horizon."""
    forward_days = HORIZON_FORWARD_DAYS.get(horizon, 5)
    cutoff = datetime.now(timezone.utc) - timedelta(days=forward_days * 2 + _CANDIDATE_MARGIN_DAYS)
    candidates = await repository.get_mature_unevaluated_signals(db, horizon, cutoff)

    outcomes = []
    for signal in candidates:
        bars = await repository.get_forward_bars(db, signal.asset_id, signal.computed_at.date(), forward_days)
        if len(bars) < forward_days + 1:
            # Pas encore assez de barres pour un rendement "plein horizon"
            # (donnees pas encore ingerees, ou marge de securite insuffisante
            # pour un actif peu liquide) - retente au prochain passage du job,
            # jamais evalue sur une fenetre partielle (le calcul serait fige
            # de facon definitive, voir unicite de signal_id).
            continue
        start_price = _return_price(bars[0])
        end_price = _return_price(bars[-1])
        if start_price == 0:
            continue
        forward_return = (end_price - start_price) / start_price
        outcomes.append(
            {
                "signal_id": signal.id,
                "asset_id": signal.asset_id,
                "horizon": horizon,
                "signal_computed_at": signal.computed_at,
                "final_signal": signal.final_signal,
                "forward_return": round(forward_return, 6),
                "was_correct": _is_correct(signal.final_signal, forward_return),
            }
        )

    saved = await repository.save_outcomes(db, outcomes)
    return saved, len(candidates)


async def evaluate_pending_outcomes(db: AsyncSession) -> dict:
    """Point d'entree du job quotidien (voir jobs/evaluate_signal_outcomes_job.py) -
    evalue tous les horizons, retourne un resume pour les logs."""
    summary = {}
    for horizon in HORIZONS:
        try:
            evaluated, candidates = await _evaluate_horizon(db, horizon)
            summary[horizon] = {"evaluated": evaluated, "candidates": candidates}
        except Exception:
            logger.exception("Echec evaluation scorecard pour l'horizon %s", horizon)
            summary[horizon] = {"evaluated": 0, "candidates": 0, "error": True}
    return summary


async def get_scorecard(db: AsyncSession) -> dict:
    """
    Precision par horizon, sur chaque fenetre glissante de
    repository.SCORECARD_WINDOWS (30/90/365 jours + tout l'historique) - le
    "score card" demande explicitement par l'utilisateur, distinct du
    backtest a la demande.
    """
    horizons_data = {}
    for horizon in HORIZONS:
        windows_data = {}
        for window_key, window_days in repository.SCORECARD_WINDOWS.items():
            windows_data[window_key] = await repository.get_window_stats(db, horizon, window_days)
        horizons_data[horizon] = windows_data
    last_evaluated_at = await repository.get_last_evaluated_at(db)
    return {"horizons": horizons_data, "last_evaluated_at": last_evaluated_at}
