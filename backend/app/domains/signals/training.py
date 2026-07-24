"""
Construction du jeu d'entrainement pour le modele statistique V2 (docs/10 et
docs/11), a partir des signaux historiques deja persistes.

Astuce de conception : plutot que d'ajouter une table/colonne dediee au
stockage des features brutes, on reutilise `signal_explanations.supporting_data`
(JSONB) - ce champ existe deja pour l'explicabilite de chaque signal (docs/06)
et contient exactement ce dont un modele a besoin (RSI, tendance, sentiment...).
Aucune migration necessaire pour demarrer l'entrainement.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_data.models import PriceBar
from app.domains.signals.models import Signal, SignalExplanation

# Fenetre de rendement futur utilisee pour labelliser un signal passe (a-t-il
# ete suivi d'une hausse ?), approximee en jours de bourse par horizon.
HORIZON_FORWARD_DAYS = {"short": 5, "medium": 20, "long": 60}


@dataclass
class TrainingExample:
    trend_up: int
    trend_down: int
    rsi_14: float
    macd_bullish: int
    volatility_20d: float
    news_sentiment: float
    news_article_count: int
    label: int  # 1 si rendement futur positif, 0 sinon
    # Etape 20 : date du signal d'origine, utilisee pour un split train/
    # validation CHRONOLOGIQUE (jamais aleatoire - un split aleatoire sur une
    # serie temporelle laisserait fuiter de l'information du futur vers le
    # passe). Optionnel/None pour ne pas casser les appels positionnels
    # existants (tests notamment) qui ne le fournissent pas.
    computed_at: datetime | None = None


async def _compute_forward_label(
    db: AsyncSession, asset_id: uuid.UUID, from_date, forward_days: int
) -> int | None:
    """Retourne 1 si le prix a monte `forward_days` plus tard, None si pas assez de donnees futures."""
    stmt = (
        select(PriceBar)
        .where(PriceBar.asset_id == asset_id, PriceBar.trade_date >= from_date)
        .order_by(PriceBar.trade_date.asc())
        .limit(forward_days + 1)
    )
    result = await db.execute(stmt)
    bars = list(result.scalars().all())
    if len(bars) < 2:
        return None
    start_price = float(bars[0].close)
    end_price = float(bars[-1].close)
    return 1 if end_price > start_price else 0


async def build_training_set(db: AsyncSession) -> list[TrainingExample]:
    """
    Parcourt tous les signaux historiques (tous actifs confondus, pour
    accumuler des exemples plus vite qu'en se limitant a un seul actif) et
    reconstruit un exemple d'entrainement par signal labellisable.
    """
    stmt = select(Signal).where(Signal.engine_version == "rules_v1")
    result = await db.execute(stmt)
    signals = list(result.scalars().all())

    examples: list[TrainingExample] = []
    for signal in signals:
        exp_result = await db.execute(
            select(SignalExplanation).where(SignalExplanation.signal_id == signal.id)
        )
        explanations = {e.component: (e.supporting_data or {}) for e in exp_result.scalars().all()}
        technical = explanations.get("technical", {})
        news = explanations.get("news", {})

        forward_days = HORIZON_FORWARD_DAYS.get(signal.horizon, 5)
        label = await _compute_forward_label(db, signal.asset_id, signal.computed_at.date(), forward_days)
        if label is None:
            continue

        examples.append(
            TrainingExample(
                trend_up=1 if technical.get("trend_direction") == "up" else 0,
                trend_down=1 if technical.get("trend_direction") == "down" else 0,
                rsi_14=float(technical.get("rsi_14") or 50.0),
                macd_bullish=1 if technical.get("macd_cross") == "bullish" else 0,
                volatility_20d=float(technical.get("volatility_20d") or 0.0),
                news_sentiment=float(news.get("news_sentiment") or 0.0),
                news_article_count=int(news.get("article_count") or 0),
                label=label,
                computed_at=signal.computed_at,
            )
        )
    return examples


def chronological_split(
    examples: list[TrainingExample], validation_fraction: float = 0.2
) -> tuple[list[TrainingExample], list[TrainingExample]]:
    """
    Etape 20 : separe les exemples en (train, validation) en respectant
    l'ordre chronologique - on entraine sur le passe, on valide sur la
    tranche la plus recente. C'est le meme principe que le walk-forward deja
    utilise en backtesting (docs/10) : un modele qui "apprend par coeur" le
    passe mais generalise mal se demasque ici par un ecart net entre
    precision d'entrainement et precision de validation (surapprentissage).

    Les exemples sans `computed_at` (anciens appels sans date) sont places en
    premier (traites comme "les plus anciens") via un tri stable.
    """
    _epoch = datetime.min.replace(tzinfo=timezone.utc)
    ordered = sorted(examples, key=lambda e: e.computed_at if e.computed_at is not None else _epoch)
    if not ordered:
        return [], []
    split_index = int(len(ordered) * (1 - validation_fraction))
    return ordered[:split_index], ordered[split_index:]
