"""
Briefing quotidien (31/07/2026) : synthese EN FRANCAIS des informations
recentes sur les titres reellement detenus (portefeuille virtuel) et/ou
suivis (watchlist) - construite a partir de donnees DEJA CALCULEES par
d'autres jobs planifies (signaux a 7h, consensus analystes a 6h30, news
ingerees en continu, voir jobs/scheduler.py) : ce module ne recalcule rien,
il lit et synthetise.

Choix delibere : pas de traduction automatique des titres d'articles (souvent
en anglais pour les valeurs US, source RSS Yahoo Finance/Google News) - une
dependance de traduction externe serait aussi fragile que les autres sources
non-contractuelles deja documentees (voir docs/17-limites-legales-
techniques.md). A la place, la synthese ("highlight_note") est GENEREE en
francais a partir de donnees structurees deja en francais (lexique de
mots-cles, libelles de signal) - le titre original reste tel quel, avec sa
source et son lien, pour verification.

`persist_state=False` (utilise par le previsualisation, voir router.py) ne
met AUCUN etat a jour : rejouer la preview plusieurs fois de suite montre
toujours "ce qui serait nouveau depuis le dernier envoi REEL", sans jamais
« consommer » les changements. Seul un vrai envoi (job planifie ou
declenchement manuel avec persist_state=True) avance ce curseur.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analyst import repository as analyst_repository
from app.domains.news import custom_keywords_repository
from app.domains.news import repository as news_repository
from app.domains.news.nlp.lexicon import KEYWORD_LEXICON
from app.domains.notifications import briefing_repository
from app.domains.notifications.mailer import send_email
from app.domains.notifications.schemas import (
    BRIEFING_DISCLAIMER,
    BriefingArticleRef,
    BriefingAssetItem,
    BriefingKeywordItem,
    BriefingRead,
    BriefingSignalItem,
)
from app.domains.notifications.service import HORIZON_LABELS, HORIZONS, SIGNAL_LABELS
from app.domains.portfolio import repository as portfolio_repository
from app.domains.signals import repository as signals_repository
from app.domains.watchlist import repository as watchlist_repository


def _sentiment_label(score: float) -> str:
    if score > 0.15:
        return "plutot positif"
    if score < -0.15:
        return "plutot negatif"
    return "neutre"


def _build_highlight_note(
    sentiment_label: str,
    average_sentiment: float,
    article_count: int,
    keywords: list[BriefingKeywordItem],
    changed_signals: list[BriefingSignalItem],
) -> str:
    """Phrase de synthese en francais - jamais une recommandation, juste un
    resume de ce qui a ete DETECTE (voir docstring de module)."""
    parts = []
    if article_count:
        base = f"Ton {sentiment_label} ({average_sentiment:+.2f}) sur {article_count} article(s) recent(s)"
        if keywords:
            top = keywords[0]
            base += f", notamment autour de « {top.keyword} » ({top.occurrences} article(s))"
        parts.append(base + ".")
    if changed_signals:
        for item in changed_signals:
            parts.append(f"Signal {item.horizon_label} : {item.signal_label}.")
    if not parts:
        parts.append("Rien de notable detecte depuis le dernier briefing.")
    return " ".join(parts)


async def build_daily_briefing(
    db: AsyncSession, window_days: int = 3, persist_state: bool = False
) -> BriefingRead:
    positions = await portfolio_repository.list_positions(db)
    watchlist_items = await watchlist_repository.list_all(db)

    # Union portefeuille + watchlist (voir choix du 31/07/2026) - un dict
    # garde une seule entree par actif meme s'il est a la fois detenu et
    # suivi, avec les deux drapeaux positionnes.
    combined: dict[uuid.UUID, dict] = {}
    for position in positions:
        combined[position.asset_id] = {
            "asset": position.asset,
            "held": True,
            "watched": False,
            "quantity_held": float(position.quantity),
        }
    for item in watchlist_items:
        entry = combined.setdefault(
            item.asset_id, {"asset": item.asset, "held": False, "watched": False, "quantity_held": None}
        )
        entry["watched"] = True

    previous_states = await briefing_repository.get_all_states(db)
    extra_lexicon = await custom_keywords_repository.as_lexicon(db)
    merged_lexicon = {**KEYWORD_LEXICON, **extra_lexicon}

    items: list[BriefingAssetItem] = []

    for asset_id, entry in combined.items():
        articles = await news_repository.get_recent_articles(db, asset_id, days=window_days)
        article_ids = [a.id for a in articles]
        scores = [float(a.sentiment_score) for a in articles if a.sentiment_score is not None]
        average_sentiment = sum(scores) / len(scores) if scores else 0.0
        sentiment_label = _sentiment_label(average_sentiment) if scores else "aucune actu recente"

        keyword_counts = await news_repository.get_keyword_counts(db, article_ids, top_n=5)
        keywords = [
            BriefingKeywordItem(
                keyword=keyword,
                weight=float(merged_lexicon.get(keyword, {}).get("weight", 0.0)),
                horizon_impact=str(merged_lexicon.get(keyword, {}).get("horizon", "medium")),
                occurrences=count,
            )
            for keyword, count in keyword_counts
        ]

        signals: list[BriefingSignalItem] = []
        changed_signals: list[BriefingSignalItem] = []
        for horizon in HORIZONS:
            signal = await signals_repository.get_latest_signal(db, asset_id, horizon)
            if signal is None:
                continue
            previous = previous_states.get((asset_id, horizon))
            changed = previous is not None and previous != signal.final_signal
            signal_item = BriefingSignalItem(
                horizon=horizon,
                horizon_label=HORIZON_LABELS[horizon],
                signal=signal.final_signal,
                signal_label=SIGNAL_LABELS.get(signal.final_signal, signal.final_signal),
                changed_since_last_briefing=changed,
            )
            signals.append(signal_item)
            if changed:
                changed_signals.append(signal_item)
            if persist_state:
                await briefing_repository.upsert_state(db, asset_id, horizon, signal.final_signal)

        consensus = await analyst_repository.get_by_asset(db, asset_id)
        consensus_label = consensus.consensus_label if consensus else None

        latest_article = None
        if articles:
            latest = articles[0]  # deja trie desc par date, voir get_recent_articles
            latest_article = BriefingArticleRef(
                title=latest.title, url=latest.url, source=latest.source, published_at=latest.published_at
            )

        highlight_note = _build_highlight_note(
            sentiment_label, average_sentiment, len(articles), keywords, changed_signals
        )

        # N'entre dans le briefing que s'il y a quelque chose de NEUF a
        # rapporter (actu recente OU signal change) - sinon on se contente de
        # calculer les etats sans polluer le digest, meme logique que
        # notifications/service.py::check_and_notify_watchlist ("rien de
        # change => rien d'envoye").
        if not articles and not changed_signals:
            continue

        items.append(
            BriefingAssetItem(
                asset=entry["asset"],
                held=entry["held"],
                watched=entry["watched"],
                quantity_held=entry["quantity_held"],
                signals=signals,
                article_count=len(articles),
                average_sentiment=round(average_sentiment, 3),
                sentiment_label=sentiment_label,
                keywords=keywords,
                consensus_label=consensus_label,
                latest_article=latest_article,
                highlight_note=highlight_note,
            )
        )

    # Tri : les titres avec un changement de signal en premier, puis par
    # nombre d'articles decroissant - les infos les plus actionnables en tete.
    items.sort(key=lambda i: (not any(s.changed_since_last_briefing for s in i.signals), -i.article_count))

    return BriefingRead(generated_at=datetime.now(timezone.utc), window_days=window_days, items=items)


def _format_email(briefing: BriefingRead) -> tuple[str, str]:
    subject = f"Bourse Assistant - Briefing quotidien ({len(briefing.items)} titre(s))"
    lines = [
        "Synthese automatique, en francais, a partir de sources tierces citees pour chaque titre.",
        "Ceci n'est pas un conseil en investissement.",
        "",
    ]
    for item in briefing.items:
        tags = []
        if item.held:
            tags.append(f"detenu ({item.quantity_held:g})" if item.quantity_held else "detenu")
        if item.watched:
            tags.append("suivi")
        lines.append(f"=== {item.asset.name} ({item.asset.ticker}) - {', '.join(tags)} ===")
        lines.append(item.highlight_note)
        if item.consensus_label:
            lines.append(f"Consensus analystes externes : {item.consensus_label}.")
        if item.latest_article:
            lines.append(
                f"Derniere source : {item.latest_article.title} ({item.latest_article.source}, "
                f"{item.latest_article.published_at:%d/%m/%Y}) - {item.latest_article.url}"
            )
        lines.append("")
    lines.append("Voir le detail sur le dashboard. Disclaimer complet : /api/v1/compliance/disclaimer.")
    return subject, "\n".join(lines)


async def send_daily_briefing(db: AsyncSession) -> BriefingRead:
    """Construit le briefing en faisant AVANCER le curseur d'etat
    (persist_state=True) et l'envoie si au moins un titre a quelque chose de
    neuf a rapporter - reutilise le mailer existant (voir mailer.py), donc
    reste silencieux tant que MAIL_ENABLED=false (comportement par defaut,
    voir docs/STACK.md)."""
    briefing = await build_daily_briefing(db, persist_state=True)
    if briefing.items:
        subject, body = _format_email(briefing)
        await send_email(subject, body)
    return briefing
