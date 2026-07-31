"""
Bac a sable pedagogique (31/07/2026) - orchestration : construit les features
(feature_engineering.py), entraine/evalue les modeles legers (models.py), et
compare le resultat au signal REEL deja calcule par le moteur de regles
(domaine signals, lecture SEULE - jamais ecrit ici) pour un meme actif/horizon.

Lecture seule egalement sur le portefeuille virtuel (domaine portfolio) :
`compare_portfolio()` reutilise les actifs deja suivis en simulation comme
jeu de test "reel" (demande explicite de l'utilisateur, 31/07/2026 - "on peut
reprendre des indices du portefeuille pour verifier par rapport a notre
calcul reelle") - aucune ecriture, aucune influence sur les positions/le cash.

Isolation stricte (voir feature_engineering.py et models.py) : ce domaine ne
modifie JAMAIS signals/backtests/portfolio - il ne fait que LIRE des donnees
qui existent deja (prix, signaux stockes, positions) pour construire une
comparaison pedagogique.
"""
import logging

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis_lab.feature_engineering import generate_all_features
from app.domains.analysis_lab.models import (
    MIN_TRAINING_SAMPLES,
    ModelResult,
    predict_arima,
    predict_ensemble,
    predict_prophet,
    predict_random_forest,
    predict_xgboost,
)
from app.domains.analysis_lab.schemas import (
    AssetComparisonRead,
    FeatureSnapshotRead,
    ModelResultRead,
    PortfolioComparisonRead,
    RealSignalSummaryRead,
)
from app.domains.assets import repository as assets_repository
from app.domains.assets.models import Asset
from app.domains.assets.schemas import AssetRead
from app.domains.market_data import repository as market_data_repository
from app.domains.portfolio import repository as portfolio_repository
from app.domains.signals import repository as signals_repository

logger = logging.getLogger(__name__)

# Duplique volontairement signals/training.py::HORIZON_FORWARD_DAYS (isolation, voir docstring de module).
HORIZON_FORWARD_DAYS = {"short": 5, "medium": 20, "long": 60}

_OHLCV_COLUMNS = ("Open", "High", "Low", "Close", "Volume")

_BULLISH_SIGNALS = ("achat_speculatif", "surveillance")


def _insufficient_data_result(model_name: str) -> ModelResult:
    return ModelResult(
        model_name=model_name,
        model_status="en_apprentissage",
        sample_count=0,
        min_required_samples=MIN_TRAINING_SAMPLES,
        probability_up=None,
        predicted_direction=None,
        explanation="Aucun historique de prix suffisant disponible pour cet actif.",
    )


async def _load_ohlcv_dataframe(db: AsyncSession, asset_id, limit: int = 500) -> pd.DataFrame:
    bars = await market_data_repository.get_price_history(db, asset_id, limit=limit)
    if not bars:
        return pd.DataFrame()
    bars = sorted(bars, key=lambda b: b.trade_date)
    rows = [
        {
            "date": bar.trade_date,
            "Open": float(bar.open),
            "High": float(bar.high),
            "Low": float(bar.low),
            "Close": float(bar.close),
            "Volume": bar.volume or 0,
        }
        for bar in bars
    ]
    df = pd.DataFrame(rows).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df


def _build_training_arrays(feat: pd.DataFrame, forward_days: int):
    """
    Construit (feature_cols, X, y, dates_valid, current_features) a partir
    d'un DataFrame de features deja calcule (generate_all_features) - utilise
    par `_run_models` (Random Forest/XGBoost, synchrones) ET par le job
    asynchrone du LSTM (Phase 3, voir jobs/deep_training_job.py) : meme
    contrat de donnees pour les deux, seule la mise en forme finale differe
    (ligne par ligne pour RF/XGBoost, sequences glissantes pour le LSTM - voir
    deep_models.py::build_sequences).
    """
    feature_cols = [c for c in feat.columns if c not in _OHLCV_COLUMNS]
    label = (feat["Close"].shift(-forward_days) > feat["Close"]).astype(float)
    valid_rows = feat[feature_cols].notna().all(axis=1) & label.notna()

    X = feat.loc[valid_rows, feature_cols].values
    y = label.loc[valid_rows].values.astype(int)
    dates_valid = feat.index[valid_rows]
    # La derniere ligne peut contenir des NaN pour les indicateurs a longue
    # fenetre (ex. sma_200 si moins de 200 barres disponibles) - remplaces par
    # 0 UNIQUEMENT pour la prediction courante (jamais pour l'entrainement,
    # ou ces lignes sont exclues via `valid_rows` ci-dessus).
    current_features = feat[feature_cols].iloc[-1].fillna(0.0).values
    return feature_cols, X, y, dates_valid, current_features


def _run_models(feat: pd.DataFrame, forward_days: int) -> list[ModelResult]:
    feature_cols, X, y, dates_valid, current_features = _build_training_arrays(feat, forward_days)

    rf_result = predict_random_forest(feature_cols, X, y, dates_valid, current_features)
    xgb_result = predict_xgboost(feature_cols, X, y, dates_valid, current_features)
    arima_result = predict_arima(feat["Close"], forward_days)
    prophet_result = predict_prophet(feat["Close"], forward_days)
    # "Ensemble" (Phase 2, 31/07/2026) : vote entre les 4 modeles ci-dessus,
    # pas un modele entraine a part - voir predict_ensemble() pour la logique.
    ensemble_result = predict_ensemble([rf_result, xgb_result, arima_result, prophet_result])
    return [rf_result, xgb_result, arima_result, prophet_result, ensemble_result]


def _to_model_read(result: ModelResult, real_bullish: bool | None) -> ModelResultRead:
    agrees = None
    if real_bullish is not None and result.predicted_direction is not None:
        agrees = (result.predicted_direction == "hausse") == real_bullish
    return ModelResultRead(
        model_name=result.model_name,
        model_status=result.model_status,
        sample_count=result.sample_count,
        min_required_samples=result.min_required_samples,
        probability_up=result.probability_up,
        predicted_direction=result.predicted_direction,
        explanation=result.explanation,
        validation_status=result.validation_status,
        train_accuracy=result.train_accuracy,
        validation_accuracy=result.validation_accuracy,
        validation_sample_count=result.validation_sample_count,
        feature_importance=result.feature_importance,
        agrees_with_real_signal=agrees,
    )


async def compare_asset(db: AsyncSession, asset: Asset, horizon: str) -> AssetComparisonRead:
    forward_days = HORIZON_FORWARD_DAYS.get(horizon, 20)
    df = await _load_ohlcv_dataframe(db, asset.id)

    if df.empty or len(df) < 30:
        model_results = [
            _insufficient_data_result("random_forest"),
            _insufficient_data_result("xgboost"),
            _insufficient_data_result("arima"),
            _insufficient_data_result("prophet"),
        ]
        # predict_ensemble() gere naturellement ce cas : aucun modele
        # exploitable (predicted_direction=None partout) -> 'en_apprentissage'.
        model_results.append(predict_ensemble(model_results))
    else:
        feat = generate_all_features(df)
        model_results = _run_models(feat, forward_days)

    real_signal_row = await signals_repository.get_latest_signal(db, asset.id, horizon)
    real_signal = None
    real_bullish = None
    if real_signal_row is not None:
        real_signal = RealSignalSummaryRead(
            final_signal=real_signal_row.final_signal,
            technical_score=float(real_signal_row.technical_score),
            news_score=float(real_signal_row.news_score),
            risk_score=float(real_signal_row.risk_score),
            confidence_score=float(real_signal_row.confidence_score),
            computed_at=real_signal_row.computed_at,
        )
        real_bullish = real_signal_row.final_signal in _BULLISH_SIGNALS

    return AssetComparisonRead(
        asset=AssetRead.model_validate(asset),
        horizon=horizon,
        real_signal=real_signal,
        models=[_to_model_read(r, real_bullish) for r in model_results],
    )


async def get_feature_snapshot(db: AsyncSession, asset: Asset) -> FeatureSnapshotRead | None:
    """Derniere valeur connue de chaque indicateur - vue "brute" pour
    repondre a 'sur quelle base est-ce calcule ?' sans passer par un modele."""
    df = await _load_ohlcv_dataframe(db, asset.id)
    if df.empty:
        return None
    feat = generate_all_features(df)
    feature_cols = [c for c in feat.columns if c not in _OHLCV_COLUMNS]
    last_row = feat[feature_cols].iloc[-1]
    features = {col: (None if pd.isna(value) else round(float(value), 6)) for col, value in last_row.items()}
    return FeatureSnapshotRead(
        asset=AssetRead.model_validate(asset),
        as_of_date=str(feat.index[-1].date()),
        features=features,
        feature_count=len(feature_cols),
    )


async def compare_asset_by_id(db: AsyncSession, asset_id, horizon: str) -> AssetComparisonRead | None:
    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        return None
    return await compare_asset(db, asset, horizon)


async def get_training_arrays_for_asset(db: AsyncSession, asset_id, horizon: str):
    """
    Phase 3 (31/07/2026) : point d'entree utilise par le job asynchrone du
    LSTM (jobs/deep_training_job.py) - memes donnees que `_run_models`
    (features + label deja alignes), mais appelees hors du cycle de requete
    HTTP synchrone de `/compare`. Retourne None si l'historique est
    insuffisant (meme seuil que compare_asset : 30 barres).
    """
    forward_days = HORIZON_FORWARD_DAYS.get(horizon, 20)
    df = await _load_ohlcv_dataframe(db, asset_id)
    if df.empty or len(df) < 30:
        return None
    feat = generate_all_features(df)
    return _build_training_arrays(feat, forward_days)


async def compare_portfolio(db: AsyncSession, horizon: str) -> PortfolioComparisonRead:
    """
    Reutilise les actifs DEJA suivis dans le portefeuille virtuel comme jeu
    de test (demande explicite de l'utilisateur) - lecture seule
    (portfolio.repository.list_positions), aucune ecriture.
    """
    positions = await portfolio_repository.list_positions(db)
    comparisons = []
    errors = []
    for position in positions:
        try:
            comparisons.append(await compare_asset(db, position.asset, horizon))
        except Exception as exc:
            logger.exception("Echec comparaison analysis_lab pour %s", position.asset.ticker)
            errors.append({"ticker": position.asset.ticker, "error": str(exc)})
    return PortfolioComparisonRead(horizon=horizon, comparisons=comparisons, errors=errors)
