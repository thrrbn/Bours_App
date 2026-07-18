"""
Decide QUAND notifier : compare le signal courant de chaque actif de la
watchlist au dernier signal pour lequel un email a deja ete envoye
(notification_states), et regroupe tous les changements detectes en un seul
email "digest" - jamais un email par actif, pour ne pas spammer (voir docs/11
et 14). N'envoie rien si rien n'a change depuis la derniere execution.
"""
import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications import repository as notif_repository
from app.domains.notifications.mailer import send_email
from app.domains.signals import repository as signals_repository
from app.domains.watchlist import repository as watchlist_repository

logger = logging.getLogger(__name__)

HORIZONS = ("short", "medium", "long")

HORIZON_LABELS = {"short": "court terme", "medium": "moyen terme", "long": "long terme"}

SIGNAL_LABELS = {
    "achat_speculatif": "Achat speculatif",
    "surveillance": "Surveillance",
    "neutre": "Neutre",
    "prudence": "Prudence",
    "vente_defensive": "Vente defensive",
}


@dataclass
class SignalChange:
    ticker: str
    name: str
    horizon: str
    previous_signal: str | None
    new_signal: str


async def check_and_notify_watchlist(db: AsyncSession) -> int:
    """
    Parcourt la watchlist, detecte les changements de signal par rapport au
    dernier etat notifie, envoie un digest unique s'il y en a, et met a jour
    notification_states. Retourne le nombre de changements detectes (0 = rien
    envoye), pour permettre au job appelant de logger un resume utile.
    """
    items = await watchlist_repository.list_all(db)
    changes: list[SignalChange] = []

    for item in items:
        if not item.notify_on_change:
            continue
        for horizon in HORIZONS:
            signal = await signals_repository.get_latest_signal(db, item.asset_id, horizon)
            if signal is None:
                continue

            state = await notif_repository.get_state(db, item.asset_id, horizon)
            previous = state.last_notified_signal if state else None

            if previous != signal.final_signal:
                changes.append(
                    SignalChange(
                        ticker=item.asset.ticker,
                        name=item.asset.name,
                        horizon=horizon,
                        previous_signal=previous,
                        new_signal=signal.final_signal,
                    )
                )
                await notif_repository.upsert_state(db, item.asset_id, horizon, signal.final_signal)

    if changes:
        await send_email(*_build_digest(changes))

    logger.info("check_and_notify_watchlist: %s changement(s) detecte(s)", len(changes))
    return len(changes)


def _build_digest(changes: list[SignalChange]) -> tuple[str, str]:
    subject = f"Bourse Assistant - {len(changes)} changement(s) de signal"
    lines = [
        "Ceci n'est pas un conseil en investissement - juste un resume des",
        "changements de signal statistique sur ta watchlist.",
        "",
    ]
    for change in changes:
        previous_label = SIGNAL_LABELS.get(change.previous_signal, "aucun signal precedent")
        new_label = SIGNAL_LABELS[change.new_signal]
        lines.append(
            f"- {change.name} ({change.ticker}) [{HORIZON_LABELS[change.horizon]}] : "
            f"{previous_label} -> {new_label}"
        )
    lines.append("")
    lines.append("Voir le detail sur le dashboard. Disclaimer complet : /api/v1/compliance/disclaimer.")
    return subject, "\n".join(lines)
