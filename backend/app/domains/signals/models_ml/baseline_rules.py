"""
Moteur de score V1 : regles ponderees, entierement explicables.
Voir docs/11-strategie-scoring-hybride.md pour la justification de chaque poids.
Ce module est LE point de calibration par backtesting - les constantes
ci-dessous sont des parametres, pas des verites figees.
"""
from dataclasses import dataclass, field

from app.domains.signals.features import SignalFeatures

ENGINE_VERSION = "rules_v1"


@dataclass
class ScoreComponent:
    name: str
    value: float
    contribution_pct: float
    explanation: str
    supporting_data: dict = field(default_factory=dict)


@dataclass
class SignalResult:
    engine_version: str
    technical_score: float
    news_score: float
    risk_score: float
    confidence_score: float
    final_signal: str
    components: list[ScoreComponent]


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def compute_technical_score(features: SignalFeatures) -> ScoreComponent:
    score = 50.0
    reasons = []

    if features.trend_direction == "up":
        score += 15
        reasons.append("la moyenne mobile 20 jours est au-dessus de la moyenne mobile 50 jours (tendance haussiere)")
    elif features.trend_direction == "down":
        score -= 15
        reasons.append("la moyenne mobile 20 jours est en dessous de la moyenne mobile 50 jours (tendance baissiere)")

    if features.rsi_14 is not None:
        if features.rsi_14 < 30:
            score += 10
            reasons.append(f"le RSI (14 jours) a {features.rsi_14:.1f} indique une zone de survente")
        elif features.rsi_14 > 70:
            score -= 10
            reasons.append(f"le RSI (14 jours) a {features.rsi_14:.1f} indique une zone de surachat")

    if features.macd_cross == "bullish":
        score += 10
        reasons.append("le MACD est au-dessus de sa ligne de signal (momentum positif)")
    elif features.macd_cross == "bearish":
        score -= 10
        reasons.append("le MACD est en dessous de sa ligne de signal (momentum negatif)")

    if features.volatility_20d is not None:
        penalty = min(15.0, features.volatility_20d * 100)
        score -= penalty
        if penalty > 5:
            reasons.append(f"la volatilite recente ({features.volatility_20d:.2%}) reduit la lisibilite du signal")

    if reasons:
        text = "Analyse technique : " + "; ".join(reasons) + "."
    else:
        text = "Analyse technique neutre, donnees insuffisantes pour degager une tendance claire."

    return ScoreComponent(
        name="technical",
        value=_clamp(score),
        contribution_pct=0.0,  # renseigne apres normalisation globale, voir compute()
        explanation=text,
        supporting_data={
            "trend_direction": features.trend_direction,
            "rsi_14": features.rsi_14,
            "macd_cross": features.macd_cross,
            "volatility_20d": features.volatility_20d,
        },
    )


def compute_news_score(features: SignalFeatures) -> ScoreComponent:
    score = 50.0 + features.news_sentiment * 50.0
    if features.news_article_count == 0:
        text = "Aucune actualite recente detectee pour cet actif sur la fenetre observee : le score news reste neutre par defaut."
    else:
        if features.news_sentiment > 0.1:
            polarity = "positif"
        elif features.news_sentiment < -0.1:
            polarity = "negatif"
        else:
            polarity = "neutre"
        text = (
            f"{features.news_article_count} article(s) recent(s) analyse(s), sentiment moyen {polarity} "
            f"({features.news_sentiment:+.2f} sur une echelle de -1 a +1)."
        )
    return ScoreComponent(
        name="news",
        value=_clamp(score),
        contribution_pct=0.0,
        explanation=text,
        supporting_data={"news_sentiment": features.news_sentiment, "article_count": features.news_article_count},
    )


def compute_risk_score(features: SignalFeatures) -> ScoreComponent:
    volatility_component = min(70.0, (features.volatility_20d or 0.0) * 300)
    score = _clamp(30.0 + volatility_component)
    text = f"Risque estime a partir d'une volatilite recente de {(features.volatility_20d or 0.0):.2%}."
    return ScoreComponent(
        name="risk", value=score, contribution_pct=0.0, explanation=text,
        supporting_data={"volatility_20d": features.volatility_20d},
    )


def compute_confidence_score(features: SignalFeatures) -> ScoreComponent:
    # En dessous de 20 jours d'historique, les indicateurs techniques (SMA20,
    # RSI...) ne sont pas encore calculables de facon fiable (voir
    # market_data/service.py) : la completude des donnees est donc nulle, quel
    # que soit par ailleurs le volume d'actualites disponible. C'est ce
    # plancher qui garantit qu'un signal ne peut jamais afficher une confiance
    # elevee sur la seule base d'actualites fraiches, sans donnees de prix
    # suffisantes (docs/11-strategie-scoring-hybride.md).
    if features.price_history_days < 20:
        data_completeness = 0.0
    else:
        data_completeness = min(1.0, features.price_history_days / 250)
    news_freshness = 1.0 if features.days_since_last_news == 0 else 0.1
    score = _clamp(100 * (0.8 * data_completeness + 0.2 * news_freshness))
    news_presence = "la presence" if features.news_article_count else "l'absence"
    text = (
        f"Confiance basee sur {features.price_history_days} jours d'historique de prix disponibles "
        f"et {news_presence} d'actualites recentes."
    )
    return ScoreComponent(
        name="confidence", value=score, contribution_pct=0.0, explanation=text,
        supporting_data={"price_history_days": features.price_history_days},
    )


def _final_signal(technical: float, news: float, risk: float, confidence: float) -> str:
    if confidence < 30:
        return "surveillance"
    combined = 0.5 * technical + 0.5 * news
    if combined >= 70 and risk < 50:
        return "achat_speculatif"
    if combined >= 55:
        return "surveillance"
    if combined <= 30 and risk >= 60:
        return "vente_defensive"
    if combined <= 45:
        return "prudence"
    return "neutre"


def compute(features: SignalFeatures) -> SignalResult:
    technical = compute_technical_score(features)
    news = compute_news_score(features)
    risk = compute_risk_score(features)
    confidence = compute_confidence_score(features)

    # Contribution relative = poids normalise de l'ecart par rapport au neutre (50),
    # simple mais suffisant pour trier les explications par importance dans l'UI.
    deviations = {"technical": abs(technical.value - 50.0), "news": abs(news.value - 50.0)}
    total_deviation = sum(deviations.values()) or 1.0
    technical.contribution_pct = round(100 * deviations["technical"] / total_deviation, 1)
    news.contribution_pct = round(100 * deviations["news"] / total_deviation, 1)

    final_signal = _final_signal(technical.value, news.value, risk.value, confidence.value)

    return SignalResult(
        engine_version=ENGINE_VERSION,
        technical_score=technical.value,
        news_score=news.value,
        risk_score=risk.value,
        confidence_score=confidence.value,
        final_signal=final_signal,
        components=[technical, news, risk, confidence],
    )
