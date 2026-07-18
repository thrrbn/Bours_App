"""
Selectionne le moteur de scoring actif et construit l'objet SignalResult
complet a partir des features. Ce fichier est le point d'extension pour
introduire un second moteur (V2, ex. regression logistique) sans changer
l'appelant (service.py).
"""
from app.domains.signals.features import SignalFeatures
from app.domains.signals.models_ml import baseline_rules
from app.domains.signals.models_ml.baseline_rules import SignalResult

ACTIVE_ENGINE = baseline_rules  # point de bascule unique vers un futur moteur V2


def generate_signal(features: SignalFeatures) -> SignalResult:
    return ACTIVE_ENGINE.compute(features)
