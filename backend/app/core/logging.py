"""Configuration du logging structure de l'application."""
import logging
import sys

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    root.handlers = [handler]
