"""Tests du calcul de metriques de backtesting (docs/06/02)."""
from app.domains.backtests.service import evaluate_signals


def test_all_correct_bullish_signals_give_perfect_precision():
    outcomes = [
        {"final_signal": "achat_speculatif", "forward_return": 0.05},
        {"final_signal": "surveillance", "forward_return": 0.02},
    ]
    metrics = evaluate_signals(outcomes)
    assert metrics.precision == 1.0
    assert metrics.false_positive_rate == 0.0


def test_wrong_direction_signals_lower_precision():
    outcomes = [
        {"final_signal": "achat_speculatif", "forward_return": -0.05},
        {"final_signal": "vente_defensive", "forward_return": 0.05},
    ]
    metrics = evaluate_signals(outcomes)
    assert metrics.precision == 0.0
    assert metrics.false_positive_rate == 1.0


def test_neutral_signals_are_excluded_from_evaluation():
    outcomes = [{"final_signal": "neutre", "forward_return": 0.1}]
    metrics = evaluate_signals(outcomes)
    assert metrics.signal_count == 1
    assert metrics.precision == 0.0  # aucun signal evaluable -> valeur par defaut


def test_empty_input_does_not_crash():
    metrics = evaluate_signals([])
    assert metrics.signal_count == 0
