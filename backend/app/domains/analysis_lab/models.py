"""
Bac a sable pedagogique (31/07/2026, voir feature_engineering.py pour le
contexte complet et docs/STACK.md pour la decision d'isolation) - modeles
"classiques" legers (Random Forest, XGBoost, ARIMA), choisis explicitement
POUR LEUR RAPIDITE (secondes, pas minutes) plutot que LSTM/GRU/Transformer
(deferres a une future iteration qui necessiterait un mecanisme de job
asynchrone, absent du projet aujourd'hui - voir discussion dans docs/STACK.md).

Meme philosophie de gouvernance que signals/models_ml/logistic_model.py (dont
ce module reprend volontairement le style - seuils de maturite, split
train/validation chronologique, diagnostic de surapprentissage) : CES
MODELES NE PRODUISENT JAMAIS DE SIGNAL OFFICIEL, ils sont affiches en
comparaison du moteur de regles reel (voir analysis_lab/service.py).

Duplication assumee avec logistic_model.py/signals.training (seuils, logique
de split) plutot qu'import croise - garde ce domaine totalement independant
du moteur de production (voir feature_engineering.py, meme choix).
"""
import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from statsmodels.tsa.arima.model import ARIMA
from xgboost import XGBClassifier

# Prophet (via cmdstanpy) journalise en INFO a chaque fit/predict ("Chain [1]
# start/done processing") - purement informatif, assourdi ici pour ne pas
# polluer les logs applicatifs a chaque appel de /compare. `setLevel` seul ne
# suffit pas (cmdstanpy reactive son propre handler autour de chaque
# fit/predict) - `propagate = False` + un NullHandler dedie coupent la
# racine explicitement.
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").addHandler(logging.NullHandler())
logging.getLogger("cmdstanpy").propagate = False
from prophet import Prophet  # noqa: E402 - doit suivre le reglage du logger ci-dessus

MIN_TRAINING_SAMPLES = 50
_MIN_FIT_SAMPLES = 10
_MIN_SPLIT_SAMPLES_PER_SIDE = 10
_VALIDATION_FRACTION = 0.2


@dataclass
class ModelResult:
    model_name: str
    model_status: str  # 'en_apprentissage' | 'fiable' | 'indisponible'
    sample_count: int
    min_required_samples: int
    probability_up: float | None
    predicted_direction: str | None  # 'hausse' | 'baisse' | None
    explanation: str
    validation_status: str = "insuffisant"  # 'insuffisant' | 'ok'
    train_accuracy: float | None = None
    validation_accuracy: float | None = None
    validation_sample_count: int = 0
    feature_importance: dict = field(default_factory=dict)  # top facteurs, vide si non applicable (ARIMA)


def chronological_split_arrays(
    X: np.ndarray, y: np.ndarray, dates: pd.DatetimeIndex, validation_fraction: float = _VALIDATION_FRACTION
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Equivalent generique de signals/training.py::chronological_split, mais
    operant sur des tableaux (X, y) plutot que sur des TrainingExample - `X`/
    `y` doivent DEJA etre ordonnes chronologiquement par `dates` (le cas dans
    ce module, ou generate_all_features() preserve l'index temporel croissant
    d'origine). Retourne (X_train, y_train, X_val, y_val).
    """
    order = np.argsort(dates.values)
    X_sorted, y_sorted = X[order], y[order]
    split_index = int(len(X_sorted) * (1 - validation_fraction))
    return X_sorted[:split_index], y_sorted[:split_index], X_sorted[split_index:], y_sorted[split_index:]


def _accuracy(model, X: np.ndarray, y: np.ndarray) -> float:
    predictions = model.predict(X)
    return float(np.mean(predictions == y))


def _evaluate_and_fit_classifier(
    model_name: str,
    build_model,
    feature_names: list[str],
    X: np.ndarray,
    y: np.ndarray,
    dates: pd.DatetimeIndex,
    current_features: np.ndarray,
) -> ModelResult:
    """
    Meme sequence que logistic_model.py::predict()/evaluate_holdout() : (1)
    split chronologique train/validation pour DIAGNOSTIQUER le
    surapprentissage, (2) reentrainement sur 100% des donnees pour la
    prediction finale (le split ne sert qu'au diagnostic, jamais a amputer le
    modele final d'exemples recents - pratique standard).
    """
    sample_count = len(y)
    if sample_count < _MIN_FIT_SAMPLES or len(set(y.tolist())) < 2:
        return ModelResult(
            model_name=model_name,
            model_status="en_apprentissage",
            sample_count=sample_count,
            min_required_samples=MIN_TRAINING_SAMPLES,
            probability_up=None,
            predicted_direction=None,
            explanation=(
                f"Pas encore assez de donnees pour entrainer {model_name} "
                f"({sample_count}/{MIN_TRAINING_SAMPLES} exemples, ou une seule classe observee)."
            ),
        )

    X_train, y_train, X_val, y_val = chronological_split_arrays(X, y, dates)
    validation_status = "insuffisant"
    train_accuracy = validation_accuracy = None
    if len(y_train) >= _MIN_SPLIT_SAMPLES_PER_SIDE and len(y_val) >= _MIN_SPLIT_SAMPLES_PER_SIDE and len(
        set(y_train.tolist())
    ) >= 2:
        diagnostic_model = build_model()
        diagnostic_model.fit(X_train, y_train)
        train_accuracy = round(_accuracy(diagnostic_model, X_train, y_train), 4)
        validation_accuracy = round(_accuracy(diagnostic_model, X_val, y_val), 4)
        validation_status = "ok"

    final_model = build_model()
    final_model.fit(X, y)
    probability_up = float(final_model.predict_proba(current_features.reshape(1, -1))[0][1])
    predicted_direction = "hausse" if probability_up >= 0.5 else "baisse"

    feature_importance = {}
    if hasattr(final_model, "feature_importances_"):
        importances = final_model.feature_importances_
        feature_importance = dict(
            sorted(zip(feature_names, importances.tolist()), key=lambda kv: abs(kv[1]), reverse=True)[:5]
        )

    model_status = "fiable" if sample_count >= MIN_TRAINING_SAMPLES else "en_apprentissage"
    prefix = (
        f"{model_name} (fiabilite suffisante)"
        if model_status == "fiable"
        else f"{model_name} (encore en apprentissage, {sample_count}/{MIN_TRAINING_SAMPLES} exemples)"
    )
    explanation = f"{prefix} : probabilite de hausse estimee a {probability_up:.0%} sur {sample_count} exemples."
    if validation_status == "ok":
        gap = round(train_accuracy - validation_accuracy, 4)
        explanation += (
            f" Train/validation : {train_accuracy:.0%} vs {validation_accuracy:.0%} "
            f"(ecart {gap:+.0%} - un grand ecart positif indiquerait du surapprentissage)."
        )
    else:
        explanation += " Historique encore trop court pour verifier le surapprentissage."

    return ModelResult(
        model_name=model_name,
        model_status=model_status,
        sample_count=sample_count,
        min_required_samples=MIN_TRAINING_SAMPLES,
        probability_up=round(probability_up, 4),
        predicted_direction=predicted_direction,
        explanation=explanation,
        validation_status=validation_status,
        train_accuracy=train_accuracy,
        validation_accuracy=validation_accuracy,
        validation_sample_count=len(y_val),
        feature_importance=feature_importance,
    )


def predict_random_forest(
    feature_names: list[str], X: np.ndarray, y: np.ndarray, dates: pd.DatetimeIndex, current_features: np.ndarray
) -> ModelResult:
    return _evaluate_and_fit_classifier(
        "random_forest",
        lambda: RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42, n_jobs=-1),
        feature_names,
        X,
        y,
        dates,
        current_features,
    )


def predict_xgboost(
    feature_names: list[str], X: np.ndarray, y: np.ndarray, dates: pd.DatetimeIndex, current_features: np.ndarray
) -> ModelResult:
    return _evaluate_and_fit_classifier(
        "xgboost",
        lambda: XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1, eval_metric="logloss", random_state=42
        ),
        feature_names,
        X,
        y,
        dates,
        current_features,
    )


def predict_arima(close: pd.Series, forward_days: int, order: tuple[int, int, int] = (5, 1, 0)) -> ModelResult:
    """
    ARIMA (AutoRegressive Integrated Moving Average) - modele UNIVARIE (ne
    consomme que la serie de cours, aucune des 70+ features de
    feature_engineering.py) : classique de reference pour situer les modeles
    ML/DL par rapport a un modele purement statistique/temporel.

    Ordre (5,1,0) fixe (pas d'auto-selection type auto_arima/pmdarima, une
    dependance supplementaire pour un gain marginal ici) - parametre ajustable,
    documente comme choix pragmatique plutot que verite figee (meme
    philosophie que le reste du projet).

    Validation walk-forward economique : plutot que reentrainer ARIMA a
    chaque pas (couteux), on ajuste l'etat du modele deja estime via
    `.append(refit=False)` (mise a jour du filtre de Kalman sans
    re-estimation des parametres) - un pas en avant, on compare la direction
    predite a la direction reelle, on ajoute l'observation reelle, on repete.
    """
    sample_count = len(close)
    if sample_count < MIN_TRAINING_SAMPLES:
        return ModelResult(
            model_name="arima",
            model_status="en_apprentissage",
            sample_count=sample_count,
            min_required_samples=MIN_TRAINING_SAMPLES,
            probability_up=None,
            predicted_direction=None,
            explanation=f"Pas encore assez d'historique pour ARIMA ({sample_count}/{MIN_TRAINING_SAMPLES} jours).",
        )

    split_index = int(sample_count * (1 - _VALIDATION_FRACTION))
    train_series = close.iloc[:split_index]
    validation_series = close.iloc[split_index:]

    validation_status = "insuffisant"
    validation_accuracy = None
    if len(validation_series) >= _MIN_SPLIT_SAMPLES_PER_SIDE:
        try:
            fitted = ARIMA(train_series.values, order=order).fit()
            correct = 0
            total = 0
            current_state = fitted
            last_value = train_series.iloc[-1]
            for actual_value in validation_series.values:
                forecast = current_state.forecast(steps=1)[0]
                predicted_up = forecast >= last_value
                actual_up = actual_value >= last_value
                if predicted_up == actual_up:
                    correct += 1
                total += 1
                current_state = current_state.append([actual_value], refit=False)
                last_value = actual_value
            if total > 0:
                validation_accuracy = round(correct / total, 4)
                validation_status = "ok"
        except Exception:
            # ARIMA peut echouer a converger sur certaines series (trop
            # plates, trop de valeurs identiques...) - traite comme
            # "diagnostic indisponible", pas comme une erreur bloquante.
            validation_status = "insuffisant"

    try:
        final_model = ARIMA(close.values, order=order).fit()
        forecast_values = final_model.forecast(steps=forward_days)
        forecast_end = forecast_values[-1]
        last_close = close.iloc[-1]
        predicted_direction = "hausse" if forecast_end >= last_close else "baisse"
        implied_return = (forecast_end - last_close) / last_close if last_close else 0.0
    except Exception as exc:
        return ModelResult(
            model_name="arima",
            model_status="indisponible",
            sample_count=sample_count,
            min_required_samples=MIN_TRAINING_SAMPLES,
            probability_up=None,
            predicted_direction=None,
            explanation=f"ARIMA n'a pas pu converger sur cette serie ({exc}).",
        )

    explanation = (
        f"ARIMA{order} : prevision a {forward_days} jours = {predicted_direction} "
        f"({implied_return:+.2%} implicite par rapport au dernier cours), base sur {sample_count} jours d'historique."
    )
    if validation_status == "ok":
        explanation += f" Precision directionnelle en validation glissante : {validation_accuracy:.0%}."
    else:
        explanation += " Historique de validation insuffisant pour un diagnostic fiable."

    model_status = "fiable" if sample_count >= MIN_TRAINING_SAMPLES else "en_apprentissage"
    return ModelResult(
        model_name="arima",
        model_status=model_status,
        sample_count=sample_count,
        min_required_samples=MIN_TRAINING_SAMPLES,
        probability_up=None,  # ARIMA ne produit pas de probabilite (modele de regression, pas de classification)
        predicted_direction=predicted_direction,
        explanation=explanation,
        validation_status=validation_status,
        train_accuracy=None,
        validation_accuracy=validation_accuracy,
        validation_sample_count=len(validation_series),
        feature_importance={},
    )


def predict_prophet(close: pd.Series, forward_days: int) -> ModelResult:
    """
    Prophet (Meta/Facebook, via cmdstanpy) - modele univarie de decomposition
    tendance + saisonnalite, deuxieme reference statistique aux cotes d'ARIMA
    (Phase 2 du plan accepte le 31/07/2026, voir docs/STACK.md). Utilise
    `close.index` (deja des dates, voir feature_engineering.py) comme colonne
    `ds` requise par Prophet.

    Saisonnalite hebdomadaire activee (les marches ont un cycle de 5 jours
    ouvres), quotidienne/annuelle desactivees (pas de signal quotidien
    intra-jour ici, et l'historique disponible - 500 barres max, voir
    service.py::_load_ohlcv_dataframe - est trop court pour estimer une
    saisonnalite annuelle de maniere fiable).

    Difference assumee avec predict_arima() : Prophet n'a pas d'equivalent a
    `.append(refit=False)` (pas de mise a jour incrementale d'etat a chaque
    pas) - le diagnostic de validation ajuste donc le modele UNE SEULE FOIS
    sur le train, puis projette tout l'horizon de validation en bloc (plutot
    qu'un pas-a-pas avec injection de la vraie valeur a chaque etape comme
    pour ARIMA). Moins strict que le walk-forward d'ARIMA, documente comme
    tel plutot que present comme equivalent.

    Note technique : les wheels PyPI de `prophet>=1.1` embarquent un binaire
    Stan precompile pour le modele Prophet standard - pas besoin d'installer
    `cmdstan` separement (`python -m cmdstanpy.install_cmdstan`) pour ce cas
    d'usage, contrairement a un usage general de cmdstanpy.
    """
    sample_count = len(close)
    if sample_count < MIN_TRAINING_SAMPLES:
        return ModelResult(
            model_name="prophet",
            model_status="en_apprentissage",
            sample_count=sample_count,
            min_required_samples=MIN_TRAINING_SAMPLES,
            probability_up=None,
            predicted_direction=None,
            explanation=f"Pas encore assez d'historique pour Prophet ({sample_count}/{MIN_TRAINING_SAMPLES} jours).",
        )

    split_index = int(sample_count * (1 - _VALIDATION_FRACTION))
    train_series = close.iloc[:split_index]
    validation_series = close.iloc[split_index:]

    validation_status = "insuffisant"
    validation_accuracy = None
    if len(validation_series) >= _MIN_SPLIT_SAMPLES_PER_SIDE:
        try:
            train_df = pd.DataFrame({"ds": train_series.index, "y": train_series.values})
            diagnostic_model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)
            diagnostic_model.fit(train_df)
            future = diagnostic_model.make_future_dataframe(periods=len(validation_series))
            forecast = diagnostic_model.predict(future)
            forecast_values = forecast["yhat"].iloc[-len(validation_series):].values
            last_value = train_series.iloc[-1]
            correct = sum(
                (predicted >= last_value) == (actual >= last_value)
                for predicted, actual in zip(forecast_values, validation_series.values)
            )
            validation_accuracy = round(correct / len(validation_series), 4)
            validation_status = "ok"
        except Exception:
            # Prophet peut echouer a converger (historique trop plat, trop
            # court...) - traite comme "diagnostic indisponible", pas bloquant.
            validation_status = "insuffisant"

    try:
        full_df = pd.DataFrame({"ds": close.index, "y": close.values})
        final_model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)
        final_model.fit(full_df)
        future = final_model.make_future_dataframe(periods=forward_days)
        forecast = final_model.predict(future)
        forecast_end = forecast["yhat"].iloc[-1]
        last_close = close.iloc[-1]
        predicted_direction = "hausse" if forecast_end >= last_close else "baisse"
        implied_return = (forecast_end - last_close) / last_close if last_close else 0.0
    except Exception as exc:
        return ModelResult(
            model_name="prophet",
            model_status="indisponible",
            sample_count=sample_count,
            min_required_samples=MIN_TRAINING_SAMPLES,
            probability_up=None,
            predicted_direction=None,
            explanation=f"Prophet n'a pas pu converger sur cette serie ({exc}).",
        )

    explanation = (
        f"Prophet : prevision a {forward_days} jours = {predicted_direction} "
        f"({implied_return:+.2%} implicite par rapport au dernier cours), base sur {sample_count} jours d'historique."
    )
    if validation_status == "ok":
        explanation += (
            f" Precision directionnelle en validation (projection en bloc, pas pas-a-pas) : {validation_accuracy:.0%}."
        )
    else:
        explanation += " Historique de validation insuffisant pour un diagnostic fiable."

    model_status = "fiable" if sample_count >= MIN_TRAINING_SAMPLES else "en_apprentissage"
    return ModelResult(
        model_name="prophet",
        model_status=model_status,
        sample_count=sample_count,
        min_required_samples=MIN_TRAINING_SAMPLES,
        probability_up=None,  # Prophet ne produit pas de probabilite (regression, pas classification)
        predicted_direction=predicted_direction,
        explanation=explanation,
        validation_status=validation_status,
        train_accuracy=None,
        validation_accuracy=validation_accuracy,
        validation_sample_count=len(validation_series),
        feature_importance={},
    )


def predict_ensemble(model_results: list[ModelResult]) -> ModelResult:
    """
    "Ensemble" au sens vote simple entre modeles DEJA calcules - pas un
    modele entraine a part entiere (pas de nouveau fit, aucune dependance
    supplementaire). Chaque modele "exploitable" (predicted_direction non
    None) vote hausse/baisse ; la direction majoritaire l'emporte. Egalite
    tranchee par la moyenne des probabilites disponibles (seuls
    Random Forest/XGBoost en produisent une - ARIMA/Prophet n'en ont pas).

    Statut 'fiable' si au moins la moitie des modeles votants sont eux-memes
    'fiable' (coherent avec MIN_TRAINING_SAMPLES par modele individuel).
    """
    votants = [r for r in model_results if r.predicted_direction is not None]
    if not votants:
        return ModelResult(
            model_name="ensemble",
            model_status="en_apprentissage",
            sample_count=0,
            min_required_samples=MIN_TRAINING_SAMPLES,
            probability_up=None,
            predicted_direction=None,
            explanation="Aucun modele individuel n'a encore produit de prediction exploitable.",
        )

    hausse_votes = [r for r in votants if r.predicted_direction == "hausse"]
    baisse_votes = [r for r in votants if r.predicted_direction == "baisse"]

    if len(hausse_votes) != len(baisse_votes):
        predicted_direction = "hausse" if len(hausse_votes) > len(baisse_votes) else "baisse"
    else:
        probs = [r.probability_up for r in votants if r.probability_up is not None]
        avg_prob = sum(probs) / len(probs) if probs else 0.5
        predicted_direction = "hausse" if avg_prob >= 0.5 else "baisse"

    probs_up = [r.probability_up for r in votants if r.probability_up is not None]
    probability_up = round(sum(probs_up) / len(probs_up), 4) if probs_up else None

    reliable_count = sum(1 for r in votants if r.model_status == "fiable")
    model_status = "fiable" if reliable_count >= (len(votants) / 2) else "en_apprentissage"

    names_hausse = ", ".join(r.model_name for r in hausse_votes) or "aucun"
    names_baisse = ", ".join(r.model_name for r in baisse_votes) or "aucun"
    explanation = (
        f"Vote parmi {len(votants)} modele(s) exploitable(s) : {len(hausse_votes)} pour la hausse ({names_hausse}), "
        f"{len(baisse_votes)} pour la baisse ({names_baisse}) -> direction retenue : {predicted_direction}."
    )

    return ModelResult(
        model_name="ensemble",
        model_status=model_status,
        sample_count=max(r.sample_count for r in votants),
        min_required_samples=MIN_TRAINING_SAMPLES,
        probability_up=probability_up,
        predicted_direction=predicted_direction,
        explanation=explanation,
        validation_status="insuffisant",
        train_accuracy=None,
        validation_accuracy=None,
        validation_sample_count=0,
        feature_importance={},
    )
