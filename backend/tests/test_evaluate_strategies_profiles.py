"""
Tests des profils de decision du scorecard hebdomadaire (14/08/2026, voir
jobs/evaluate_strategies_job.py::DECISION_PROFILES) - fonctions pures
(aucune DB requise, meme convention que test_backtests_metrics.py).
"""
from app.domains.signals.models_ml.baseline_rules import classify_signal
from app.jobs.evaluate_strategies_job import DECISION_PROFILES, _profile_strategy_name


def test_profile_strategy_name_suffixes_non_default_profiles():
    assert _profile_strategy_name("internal_rules", "prudent") == "internal_rules::prudent"
    assert _profile_strategy_name("signal_replay", "agressif") == "signal_replay::agressif"


def test_profile_strategy_name_leaves_default_profile_unsuffixed():
    assert _profile_strategy_name("internal_rules", "") == "internal_rules"


def test_default_profile_is_none_to_preserve_stored_final_signal():
    # "" doit rester None : c'est ce qui fait que le profil par defaut
    # reutilise le final_signal DEJA stocke (voir service.py::run_backtest_for_asset)
    # plutot que de reclassifier - comportement de production inchange.
    assert DECISION_PROFILES[""] is None


def test_profile_thresholds_preserve_buy_watch_caution_sell_ordering():
    for name, params in DECISION_PROFILES.items():
        if params is None:
            continue
        assert params.buy_threshold > params.watch_threshold > params.caution_threshold > params.sell_threshold, name


def test_prudent_profile_is_stricter_than_default_and_agressif():
    prudent = DECISION_PROFILES["prudent"]
    agressif = DECISION_PROFILES["agressif"]
    assert prudent.buy_threshold > agressif.buy_threshold
    assert prudent.buy_max_risk < agressif.buy_max_risk
    assert prudent.min_confidence > agressif.min_confidence


def test_profiles_can_classify_the_same_scores_differently():
    # Score "moyen-haut" : achat sous le profil agressif (seuil bas), mais
    # seulement surveillance sous le profil prudent (seuil plus exigeant) -
    # demontre que les profils produisent bien des decisions distinctes sur
    # le meme historique de scores, pas juste des metadonnees cosmetiques.
    technical, news, risk, confidence = 65.0, 65.0, 45.0, 50.0
    agressif_signal = classify_signal(technical, news, risk, confidence, params=DECISION_PROFILES["agressif"])
    prudent_signal = classify_signal(technical, news, risk, confidence, params=DECISION_PROFILES["prudent"])
    assert agressif_signal == "achat_speculatif"
    assert prudent_signal != "achat_speculatif"
