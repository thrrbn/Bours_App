"""
Orchestration du domaine analyst : recuperation du consensus externe,
comparaison avec nos propres signaux (moteur de regles + apercu ML), et
alertes portefeuille virtuel. Rien ici n'est notre propre recommandation -
voir schemas.py pour les disclaimers systematiques.

Seuils de classification du consensus (arbitraires, documentes ici) :
  consensus_score = (2*strong_buy + buy - sell - 2*strong_sell) / total
  >= 0.5  -> 'achat' ; <= -0.5 -> 'vente' ; sinon 'neutre'
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AssetNotFoundError
from app.domains.analyst import repository
from app.domains.analyst.models import AnalystConsensus
from app.domains.analyst.provider import fetch_consensus
from app.domains.analyst.schemas import AnalystConsensusRead, ComparisonRead, PortfolioAlertRead
from app.domains.assets import repository as assets_repository
from app.domains.market_data import repository as market_data_repository
from app.domains.news import repository as news_repository
from app.domains.portfolio import repository as portfolio_repository
from app.domains.signals import service as signals_service
from app.domains.signals.training import TrainingExample, build_training_set

CONSENSUS_BUY_THRESHOLD = 0.5
CONSENSUS_SELL_THRESHOLD = -0.5

# Simplification a 3 categories du vocabulaire a 5 niveaux du moteur de regles
# (docs/11), pour permettre une comparaison directe avec le consensus externe.
RULES_DIRECTION_MAP = {
    "achat_speculatif": "achat",
    "surveillance": "neutre",
    "neutre": "neutre",
    "prudence": "vente",
    "vente_defensive": "vente",
}


def _score_and_label(strong_buy: int, buy: int, hold: int, sell: int, strong_sell: int) -> tuple[float, str]:
    total = strong_buy + buy + hold + sell + strong_sell
    if total == 0:
        return 0.0, "neutre"
    score = (2 * strong_buy + buy - sell - 2 * strong_sell) / total
    if score >= CONSENSUS_BUY_THRESHOLD:
        label = "achat"
    elif score <= CONSENSUS_SELL_THRESHOLD:
        label = "vente"
    else:
        label = "neutre"
    return round(score, 3), label


def _to_read(consensus: AnalystConsensus) -> AnalystConsensusRead:
    return AnalystConsensusRead(
        asset=consensus.asset,
        strong_buy=consensus.strong_buy,
        buy=consensus.buy,
        hold=consensus.hold,
        sell=consensus.sell,
        strong_sell=consensus.strong_sell,
        consensus_score=consensus.consensus_score,
        consensus_label=consensus.consensus_label,
        fetched_at=consensus.fetched_at,
    )


async def refresh_for_asset(db: AsyncSession, asset_id: uuid.UUID) -> AnalystConsensusRead | None:
    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))

    dto = fetch_consensus(asset.ticker)
    if dto is None:
        return None  # pas de couverture analyste pour ce titre - pas une erreur

    score, label = _score_and_label(dto.strong_buy, dto.buy, dto.hold, dto.sell, dto.strong_sell)
    consensus = await repository.upsert(
        db, asset_id, dto.strong_buy, dto.buy, dto.hold, dto.sell, dto.strong_sell, score, label
    )
    return _to_read(consensus)


async def get_top_buys(db: AsyncSession, limit: int = 10) -> list[AnalystConsensusRead]:
    all_consensus = await repository.list_all(db)
    ranked = sorted(all_consensus, key=lambda c: c.consensus_score, reverse=True)
    return [_to_read(c) for c in ranked[:limit]]


async def refresh_all(db: AsyncSession) -> dict:
    """Rafraichit le consensus pour tous les actifs connus, en une seule
    requete - meme logique que le job planifie (refresh_analyst_ratings_job),
    mais declenchable a la demande sans attendre 6h30."""
    assets = await assets_repository.list_all(db)
    covered = 0
    errors = 0
    for asset in assets:
        try:
            result = await refresh_for_asset(db, asset.id)
            if result is not None:
                covered += 1
        except Exception:
            errors += 1
    return {"total_assets": len(assets), "covered": covered, "errors": errors}


async def get_portfolio_alerts(db: AsyncSession) -> list[PortfolioAlertRead]:
    """Actifs du portefeuille virtuel pour lesquels le consensus externe dit
    'vendre' - une proposition a considerer, jamais un ordre automatique."""
    positions = await portfolio_repository.list_positions(db)
    alerts: list[PortfolioAlertRead] = []

    for position in positions:
        consensus = await repository.get_by_asset(db, position.asset_id)
        if consensus is None or consensus.consensus_label != "vente":
            continue

        bar = await market_data_repository.get_latest_bar(db, position.asset_id)
        alerts.append(
            PortfolioAlertRead(
                asset=position.asset,
                consensus_label=consensus.consensus_label,
                consensus_score=consensus.consensus_score,
                quantity_held=float(position.quantity),
                avg_cost=float(position.avg_cost),
                current_price=float(bar.close) if bar else None,
                note=(
                    "Les analystes externes penchent vers la vente sur ce titre que tu detiens en simulation - "
                    "a considerer, ce n'est pas un ordre automatique."
                ),
            )
        )
    return alerts


async def get_comparison(
    db: AsyncSession, asset_id: uuid.UUID, horizon: str, training_examples: list[TrainingExample] | None = None
) -> ComparisonRead:
    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))

    signal = await signals_service.get_or_compute_signal(db, asset_id, horizon, training_examples=training_examples)
    rules_direction = RULES_DIRECTION_MAP.get(signal.final_signal, "neutre")

    ml_direction = None
    ml_status = None
    if signal.ml_preview is not None:
        ml_status = signal.ml_preview.model_status
        if ml_status == "fiable" and signal.ml_preview.final_signal:
            ml_direction = RULES_DIRECTION_MAP.get(signal.ml_preview.final_signal, "neutre")

    consensus = await repository.get_by_asset(db, asset_id)
    external_label = consensus.consensus_label if consensus else None
    external_score = consensus.consensus_score if consensus else None

    agreement_rules = (rules_direction == external_label) if external_label is not None else None
    agreement_ml = (ml_direction == external_label) if (ml_direction is not None and external_label is not None) else None

    articles = await news_repository.get_recent_articles(db, asset_id, days=14)

    if external_label is None:
        note = "Aucune couverture d'analystes externes trouvee pour ce titre (frequent sur les valeurs europeennes de taille moyenne)."
    elif agreement_ml is not None:
        note = "Comparaison basee sur le moteur de regles et le modele ML (desormais fiable)."
    else:
        note = "Comparaison basee uniquement sur le moteur de regles - le modele ML n'est pas encore fiable."

    return ComparisonRead(
        asset=asset,
        horizon=horizon,
        internal_rules_signal=signal.final_signal,
        internal_rules_direction=rules_direction,
        internal_ml_status=ml_status,
        internal_ml_direction=ml_direction,
        external_consensus_label=external_label,
        external_consensus_score=external_score,
        agreement_rules=agreement_rules,
        agreement_ml=agreement_ml,
        recent_articles=articles[:5],
        note=note,
    )


async def get_comparison_table(db: AsyncSession, horizon: str) -> list[ComparisonRead]:
    """
    Version "hit parade" de get_comparison : une ligne par actif connu,
    triee par score de consensus externe decroissant, pour voir d'un coup
    d'oeil ou notre moteur de regles / modele ML sont d'accord ou pas avec
    les analystes externes - le but etant de juger visuellement, au fil du
    temps, laquelle des deux sources colle le mieux a la realite (voir
    docs/11, section modele statistique V2).

    Bug de performance reel corrige le 30/07/2026 : chaque ligne appelait
    signals_service.get_or_compute_signal(), qui reconstruisait
    integralement le jeu d'entrainement ML (build_training_set - un
    aller-retour DB par signal existant, tous actifs confondus) A CHAQUE
    ACTIF. Avec 20-30 actifs c'etait lent mais tolerable ; avec l'univers
    elargi (~189 actifs possibles depuis le seed CAC40/DAX40/AEX/US), ce
    O(nb_actifs x nb_signaux) rendait l'endpoint quasi infini ("tourne en
    boucle"). Desormais construit UNE SEULE FOIS ici et reutilise pour
    chaque ligne - meme correctif applique a jobs/compute_signals_job.py,
    qui avait exactement le meme defaut pour le cron quotidien.
    """
    training_examples = await build_training_set(db)
    assets = await assets_repository.list_all(db)
    rows: list[ComparisonRead] = []
    for asset in assets:
        try:
            rows.append(await get_comparison(db, asset.id, horizon, training_examples=training_examples))
        except Exception:
            continue  # actif sans historique suffisant pour un signal - on l'exclut du tableau, pas d'erreur globale

    rows.sort(key=lambda r: (r.external_consensus_score is None, -(r.external_consensus_score or 0)))
    return rows
