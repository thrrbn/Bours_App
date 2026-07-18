"""Garde-fous automatises sur la formulation des textes generes (docs/17)."""
import unicodedata

from app.domains.compliance.disclaimers import FORBIDDEN_TERMS


def _normalize(text: str) -> str:
    text = text.lower()
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def validate_signal_wording(text: str) -> None:
    """Leve une ValueError si le texte contient un terme interdit par la gouvernance du risque."""
    normalized = _normalize(text)
    for term in FORBIDDEN_TERMS:
        if _normalize(term) in normalized:
            raise ValueError(f"Formulation non conforme detectee ('{term}') dans le texte genere: {text!r}")
