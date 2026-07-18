"""Tests du garde-fou de formulation des signaux (docs/17)."""
import pytest

from app.domains.compliance.guardrails import validate_signal_wording


def test_acceptable_wording_passes():
    validate_signal_wording("Le RSI indique une zone de survente, signal de surveillance.")


def test_forbidden_term_raises_error():
    with pytest.raises(ValueError):
        validate_signal_wording("Ce placement est garanti sans risque.")


def test_forbidden_term_case_and_accent_insensitive():
    with pytest.raises(ValueError):
        validate_signal_wording("Vous devez ACHETER maintenant, gain GARANTI.")
