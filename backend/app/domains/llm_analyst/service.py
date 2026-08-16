"""
Orchestration du domaine llm_analyst (16/08/2026, voir docs/20-instance-locale-pc-mac.md).

Assemble `backtests/kernc_engine.py::run_kernc_backtest_raw` + `quant_facts` +
`llm_provider` + `analyst` en un rapport final - exactement le meme
assemblage que `tools/backtest_analyst/cli.py`, mais a partir de la base de
donnees locale (cours AJUSTES des dividendes/splits, voir kernc_engine.py::
_load_price_dataframe) plutot que de l'API publique en lecture seule du NAS
(cours bruts uniquement) - les deux peuvent donc legerement diverger, voir
docs/20 pour le detail.
"""
from __future__ import annotations

import asyncio
import math
import uuid
from datetime import date

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AssetNotFoundError, InsufficientDataError
from app.domains.assets import repository as assets_repository
from app.domains.backtests.kernc_engine import LLM_ANALYST_SUPPORTED_STRATEGIES, run_kernc_backtest_raw
from app.domains.llm_analyst import quant_facts
from app.domains.llm_analyst.analyst import analyze
from app.domains.llm_analyst.llm_provider import OllamaProvider

# Memes cles/logique que tools/backtest_analyst/backtest_runner.py::_STATS_KEYS
# et ::_num - dupliquees ici pour la meme raison que le reste du domaine
# (voir docstring de quant_facts.py) : la sortie brute de bt.run() (pd.Series)
# contient des Timestamps/Timedeltas et des cles non-scalaires
# (_strategy/_equity_curve/_trades) qui ne passeraient pas json.dumps() tel
# quel dans analyst.py::build_prompt.
_STATS_KEYS = (
    "# Trades",
    "Win Rate [%]",
    "Return [%]",
    "Buy & Hold Return [%]",
    "Return (Ann.) [%]",
    "Volatility (Ann.) [%]",
    "Max. Drawdown [%]",
    "Avg. Drawdown [%]",
    "Sharpe Ratio",
    "Sortino Ratio",
    "Calmar Ratio",
    "Profit Factor",
    "SQN",
    "Best Trade [%]",
    "Worst Trade [%]",
    "Avg. Trade [%]",
    "Exposure Time [%]",
)


def _num(value) -> float | None:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "total_seconds"):
        return round(value.total_seconds() / 86400, 2)
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isinf(result) else result


async def run_analysis(
    db: AsyncSession,
    asset_id: uuid.UUID,
    strategy_name: str,
    period_start: date,
    period_end: date,
    model_name: str | None,
) -> dict:
    """Fait tout le travail d'une analyse : rejoue le backtest, calcule les
    faits, appelle le LLM, valide, rend le markdown. Appelee depuis
    jobs/llm_analysis_job.py (tache de fond) - jamais directement depuis le
    router (voir router.py, meme pattern que analysis_lab/deep_training_job.py).
    Leve ValueError/AssetNotFoundError/InsufficientDataError - a capturer
    par l'appelant pour marquer le job 'failed'.

    L'appel au LLM (provider.complete -> httpx synchrone, jusqu'a plusieurs
    minutes pour un modele lourd) est deporte via `asyncio.to_thread` pour ne
    pas geler la boucle asyncio pendant ce temps - toutes les autres requetes
    de cette instance locale (frontend inclus) resteraient sinon bloquees
    tant que le modele n'a pas repondu."""
    if strategy_name not in LLM_ANALYST_SUPPORTED_STRATEGIES:
        raise ValueError(
            f"Strategie non supportee par l'analyste IA: {strategy_name} "
            f"(supportees: {LLM_ANALYST_SUPPORTED_STRATEGIES})"
        )

    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))

    raw = await run_kernc_backtest_raw(db, asset_id, strategy_name, period_start, period_end)
    if raw is None:
        raise InsufficientDataError(
            f"Historique de prix insuffisant pour {asset.ticker} sur cette periode - lance d'abord un import "
            f"(voir docs/20-instance-locale-pc-mac.md : python -m app.jobs.import_from_nas)."
        )

    scalar_stats = {key: _num(raw.stats[key]) for key in _STATS_KEYS if key in raw.stats}
    facts = quant_facts.build_facts(raw.price_df, raw.trades, raw.equity_curve, scalar_stats)

    settings = get_settings()
    provider = OllamaProvider(model=model_name or settings.ollama_model)
    report = await asyncio.to_thread(analyze, provider, strategy_name, asset.ticker, period_start, period_end, facts)

    return {
        "markdown": report.markdown,
        "citation_warnings": report.citation_warnings,
        "low_sample_warning": report.low_sample_warning,
        "from_cache": report.from_cache,
        "model": report.model,
    }
