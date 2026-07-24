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


def test_financial_metrics_none_with_fewer_than_two_evaluable_signals():
    outcomes = [{"final_signal": "achat_speculatif", "forward_return": 0.05}]
    metrics = evaluate_signals(outcomes)
    assert metrics.sharpe_ratio is None
    assert metrics.calmar_ratio is None
    assert metrics.profit_factor is None
    assert metrics.avg_risk_reward is None


def test_financial_metrics_computed_with_mixed_outcomes():
    outcomes = [
        {"final_signal": "achat_speculatif", "forward_return": 0.10},
        {"final_signal": "achat_speculatif", "forward_return": -0.04},
        {"final_signal": "vente_defensive", "forward_return": -0.06},
        {"final_signal": "vente_defensive", "forward_return": 0.02},
    ]
    metrics = evaluate_signals(outcomes)
    # strategy returns : +0.10, -0.04, +0.06 (vente correcte), -0.02 (vente ratee)
    assert metrics.sharpe_ratio is not None
    assert metrics.profit_factor is not None
    assert metrics.profit_factor > 0
    assert metrics.avg_risk_reward is not None
    # 2 gains (0.10, 0.06) et 2 pertes (0.04, 0.02) -> profit factor = 0.16/0.06
    assert metrics.profit_factor == round(0.16 / 0.06, 4)


def test_profit_factor_none_when_no_losses():
    outcomes = [
        {"final_signal": "achat_speculatif", "forward_return": 0.05},
        {"final_signal": "achat_speculatif", "forward_return": 0.03},
    ]
    metrics = evaluate_signals(outcomes)
    assert metrics.profit_factor is None  # pas de pertes -> ratio non defini
    assert metrics.avg_risk_reward is None  # pas de perte moyenne -> non defini
