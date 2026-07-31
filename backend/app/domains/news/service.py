"""Orchestration : ingestion des articles, scoring de sentiment, extraction de mots-cles."""
import html as html_lib
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domains.assets import repository as assets_repository
from app.domains.news import custom_keywords_repository, repository
from app.domains.news.custom_keywords_models import CustomKeyword
from app.domains.news.nlp.keywords import extract_keywords
from app.domains.news.nlp.sentiment import score_sentiment
from app.domains.news.nlp.translation import translate_to_french
from app.domains.news.providers.base import NewsProvider

HORIZONS = ("short", "medium", "long")


async def ingest_and_score(
    db: AsyncSession, asset_id: uuid.UUID, ticker: str, company_name: str, provider: NewsProvider
) -> int:
    articles = await provider.fetch_articles(ticker, company_name)
    if not articles:
        return 0

    # Mots-cles personnalises (voir custom_keywords_repository.py) fusionnes
    # au lexique fixe pour CETTE ingestion - une seule requete pour tous les
    # articles de cet appel plutot qu'une par article.
    extra_lexicon = await custom_keywords_repository.as_lexicon(db)

    new_count = 0
    for article in articles:
        if await repository.exists_by_url(db, article.url):
            continue
        text_for_analysis = f"{article.title} {article.raw_content or ''}"
        sentiment = score_sentiment(text_for_analysis, extra_lexicon=extra_lexicon)
        keyword_matches = extract_keywords(text_for_analysis, extra_lexicon=extra_lexicon)
        await repository.create_article_with_keywords(
            db, asset_id=asset_id, article=article, sentiment=sentiment, keyword_matches=keyword_matches
        )
        new_count += 1
    return new_count


async def list_custom_keywords(db: AsyncSession) -> list[CustomKeyword]:
    return await custom_keywords_repository.list_all(db)


async def add_custom_keyword(db: AsyncSession, keyword: str, weight: float, horizon_impact: str) -> CustomKeyword:
    """Idempotent : si le mot-cle existe deja (insensible a la casse via
    normalisation cote appelant/frontend), met a jour son poids/horizon
    plutot que de lever une erreur de doublon."""
    normalized = keyword.strip()
    if not normalized:
        raise ValueError("Mot-cle vide.")
    if horizon_impact not in HORIZONS:
        horizon_impact = "medium"

    existing = await custom_keywords_repository.get_by_keyword(db, normalized)
    if existing is not None:
        await custom_keywords_repository.delete(db, existing)
    return await custom_keywords_repository.create(db, normalized, weight, horizon_impact)


async def delete_custom_keyword(db: AsyncSession, keyword_id: uuid.UUID) -> None:
    row = await custom_keywords_repository.get_by_id(db, keyword_id)
    if row is None:
        raise NotFoundError("Mot-cle", str(keyword_id))
    await custom_keywords_repository.delete(db, row)


async def rescan_keywords(db: AsyncSession, asset_id: uuid.UUID | None = None) -> dict:
    """
    31/07/2026 : repasse les articles DEJA en base au lexique ACTUEL (fixe +
    mots-cles personnalises) - contrairement a ingest_and_score, ne va rien
    chercher de nouveau sur les flux RSS. Corrige le cas ou un mot-cle est
    ajoute APRES qu'un article pertinent ait deja ete ingere : jusqu'ici, le
    matching ne se faisait qu'a l'ingestion (voir ingest_and_score), et
    exists_by_url empechait tout re-scoring au rafraichissement suivant -
    un mot-cle ajoute apres coup ne s'appliquait donc jamais retroactivement.

    Sans asset_id : rescanne TOUS les articles connus (utilise depuis la page
    Briefing, ou les mots-cles personnalises sont geres globalement).
    """
    extra_lexicon = await custom_keywords_repository.as_lexicon(db)
    articles = await repository.get_all_articles(db, asset_id=asset_id)

    total_matches = 0
    for article in articles:
        text_for_analysis = f"{article.title} {article.raw_content or ''}"
        sentiment = score_sentiment(text_for_analysis, extra_lexicon=extra_lexicon)
        keyword_matches = extract_keywords(text_for_analysis, extra_lexicon=extra_lexicon)
        await repository.replace_keyword_matches(db, article, sentiment, keyword_matches)
        total_matches += len(keyword_matches)

    return {"articles_rescanned": len(articles), "total_keyword_matches": total_matches}


async def get_keyword_matches(db: AsyncSession, keyword: str | None = None, limit: int = 50) -> list[dict]:
    """
    Articles (toutes dates, tous actifs suivis) qui matchent un mot-cle
    PERSONNALISE - reponse directe a "ou est-ce que ca apparait" pour un
    mot-cle ajoute par l'utilisateur (voir custom_keywords_repository.py).
    Sans `keyword` : tous les mots-cles personnalises actuellement definis.
    Ne porte JAMAIS sur le lexique fixe (16 termes generiques, voir
    nlp/lexicon.py) - volontairement scope aux mots-cles choisis par
    l'utilisateur, sans quoi ce serait noye dans le volume du lexique fixe.
    """
    custom = await custom_keywords_repository.list_all(db)
    known_names = {row.keyword for row in custom}
    if keyword:
        keyword_names = [keyword]
    else:
        keyword_names = list(known_names)
    if not keyword_names:
        return []

    rows = await repository.get_articles_by_keywords(db, keyword_names, limit=limit)
    asset_ids = {article.asset_id for article, _ in rows if article.asset_id}
    assets = await assets_repository.get_many_by_ids(db, list(asset_ids))
    asset_map = {asset.id: asset for asset in assets}

    return [
        {
            "keyword": match.keyword,
            "weight": match.weight,
            "horizon_impact": match.horizon_impact,
            "occurrences": match.occurrences,
            "article": article,
            "asset_ticker": asset_map[article.asset_id].ticker if article.asset_id in asset_map else None,
            "asset_name": asset_map[article.asset_id].name if article.asset_id in asset_map else None,
        }
        for article, match in rows
    ]


def _sentiment_label(score: float) -> str:
    """Meme convention que notifications/briefing_service.py::_sentiment_label
    (duplique volontairement plutot qu'importe - eviter un couplage
    news -> notifications alors que c'est deja notifications -> news)."""
    if score > 0.15:
        return "ton plutot positif"
    if score < -0.15:
        return "ton plutot negatif"
    return "ton neutre"


def _clean_html(text: str) -> str:
    """Nettoyage regex simple (pas de dependance type BeautifulSoup) - les
    flux RSS (surtout Google News) melangent souvent du HTML dans le champ
    'summary' (ex. balises <a>/<font> autour du lien source). Suffisant pour
    un extrait de quelques phrases, pas un parseur HTML complet."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _split_sentences(text: str) -> list[str]:
    """Decoupage simple sur ponctuation forte - pas un tokenizer NLP, mais
    les extraits RSS sont deja courts (1-3 phrases en general)."""
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


async def summarize_article(db: AsyncSession, article_id: uuid.UUID, max_lines: int = 10) -> list[str]:
    """
    Resume EN FRANCAIS d'un article precis, plafonne a `max_lines` - meta
    (source/date/actif), ton detecte, mots-cles matches SUR CET article, puis
    l'extrait fourni par le flux RSS (nettoye du HTML), decoupe en phrases.

    Limite honnete : ce n'est PAS un resume du texte integral de l'article -
    l'app n'a jamais le texte complet (RSS uniquement, voir providers/
    rss_provider.py), et ne fait pas de scraping du site source (fragile,
    contraire a la discipline du projet sur les sources non-contractuelles,
    voir docs/17-limites-legales-techniques.md). Quand le flux ne fournit
    quasiment rien (frequent sur Google News, dont le "summary" est souvent
    juste un lien+source), le resume reste court - c'est le maximum
    honnetement disponible sans dependance supplementaire.
    """
    article = await repository.get_article_by_id(db, article_id)
    if article is None:
        raise NotFoundError("Article", str(article_id))

    lines: list[str] = []

    # Titre traduit en premiere ligne - voir nlp/translation.py (degradation
    # gracieuse : renvoie le titre original si la traduction echoue).
    if article.title:
        lines.append(translate_to_french(article.title))

    meta = f"{article.source} - {article.published_at:%d/%m/%Y}"
    if article.asset_id:
        asset = await assets_repository.get_by_id(db, article.asset_id)
        if asset:
            meta += f" - {asset.ticker} ({asset.name})"
    lines.append(meta)

    if article.sentiment_score is not None:
        score = float(article.sentiment_score)
        lines.append(f"{_sentiment_label(score)} (score {score:+.2f}).")

    keyword_matches = await repository.get_keyword_matches_for_article(db, article_id)
    if keyword_matches:
        top = sorted(keyword_matches, key=lambda m: -m.occurrences)[:5]
        lines.append("Mots-cles detectes : " + ", ".join(f"« {m.keyword} »" for m in top) + ".")

    remaining = max_lines - len(lines)
    if remaining > 0:
        if article.raw_content:
            cleaned = _clean_html(article.raw_content)
            # Traduit le bloc ENTIER avant de decouper en phrases (une seule
            # requete, garde le contexte) plutot que de traduire phrase par
            # phrase - voir nlp/translation.py.
            translated = translate_to_french(cleaned)
            sentences = _split_sentences(translated)
            if sentences:
                lines.extend(sentences[:remaining])
            else:
                lines.append("Extrait RSS vide ou illisible - voir l'article source pour le detail.")
        else:
            lines.append("Aucun extrait fourni par le flux RSS - voir l'article source pour le detail.")

    return lines[:max_lines]


async def get_keyword_matches_summary(db: AsyncSession, max_lines: int = 10) -> list[str]:
    """
    Resume EN FRANCAIS des correspondances de mots-cles personnalises - une
    ligne par mot-cle (nombre d'articles, actif(s) concerne(s), date du plus
    recent, ton moyen), triees par activite la plus recente, plafonnees a
    `max_lines`. Genere a partir de donnees deja structurees (pas de
    traduction/IA generative - meme choix que le briefing quotidien, voir
    notifications/briefing_service.py pour la discussion complete).
    """
    matches = await get_keyword_matches(db, keyword=None, limit=500)
    if not matches:
        return []

    groups: dict[str, list[dict]] = {}
    for match in matches:
        groups.setdefault(match["keyword"], []).append(match)

    def most_recent(group: list[dict]):
        return max(m["article"].published_at for m in group)

    ordered = sorted(groups.items(), key=lambda kv: most_recent(kv[1]), reverse=True)

    lines: list[str] = []
    for keyword, group in ordered[:max_lines]:
        count = len(group)
        tickers = sorted({m["asset_ticker"] for m in group if m["asset_ticker"]})
        tickers_str = ", ".join(tickers[:3]) + (", ..." if len(tickers) > 3 else "") if tickers else "actif non identifie"
        latest = max(group, key=lambda m: m["article"].published_at)
        scores = [float(m["article"].sentiment_score) for m in group if m["article"].sentiment_score is not None]
        sentiment_text = _sentiment_label(sum(scores) / len(scores)) if scores else "ton non determine"
        lines.append(
            f"« {keyword} » : {count} article(s) ({tickers_str}), dernier le "
            f"{latest['article'].published_at:%d/%m/%Y} - {sentiment_text}."
        )
    return lines


async def get_sentiment_summary(db: AsyncSession, asset_id: uuid.UUID, days: int = 7) -> dict:
    articles = await repository.get_recent_articles(db, asset_id, days=days)
    if not articles:
        return {"article_count": 0, "average_sentiment": 0.0, "dominant_keywords": []}

    scores = [float(a.sentiment_score) for a in articles if a.sentiment_score is not None]
    average_sentiment = sum(scores) / len(scores) if scores else 0.0
    dominant_keywords = await repository.get_dominant_keywords(db, [a.id for a in articles])
    return {
        "article_count": len(articles),
        "average_sentiment": average_sentiment,
        "dominant_keywords": dominant_keywords,
    }
