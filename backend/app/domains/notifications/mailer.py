"""
Envoi d'email brut via SMTP (aiosmtplib, non-bloquant). Aucune logique
metier ici (voir service.py pour la decision de quand notifier) - ce module
sait uniquement "envoyer ce texte a cette adresse", et respecte MAIL_ENABLED
pour rester silencieux tant que l'utilisateur n'a pas configure ses propres
identifiants SMTP dans son .env local.
"""
import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_email(subject: str, body: str) -> bool:
    settings = get_settings()

    if not settings.mail_enabled:
        logger.info("MAIL_ENABLED=false - envoi ignore (sujet: %s)", subject)
        return False

    if not settings.mail_user or not settings.mail_password:
        logger.warning("MAIL_USER/MAIL_PASSWORD manquants - envoi impossible (sujet: %s)", subject)
        return False

    recipient = settings.notify_email or settings.mail_user

    message = EmailMessage()
    message["From"] = settings.mail_from or settings.mail_user
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.mail_server,
            port=settings.mail_port,
            start_tls=True,
            username=settings.mail_user,
            password=settings.mail_password,
        )
        logger.info("Email envoye a %s (sujet: %s)", recipient, subject)
        return True
    except Exception:
        logger.exception("Echec de l'envoi d'email (sujet: %s)", subject)
        return False
