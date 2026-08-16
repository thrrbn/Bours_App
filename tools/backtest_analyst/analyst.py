"""
Orchestrateur (14/08/2026) : assemble backtest_runner + quant_facts +
llm_provider en un rapport final. C'est le SEUL endroit ou le prompt envoye
au LLM est construit, et le SEUL endroit ou sa reponse est validee avant
d'etre presentee - toute la discipline decidee dans la conversation du
14/08/2026 (faits precalcules uniquement, citations obligatoires, seuil
minimum de transactions) est appliquee ici.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from llm_provider import LLMProvider

MIN_TRADES_FOR_NARRATIVE = 15

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": (
                "2-4 phrases SUBSTANTIELLES (jamais une reformulation du titre/de la periode - voir regle 8) : "
                "doit mentionner le rendement total obtenu (aggregate_stats), le compare au rendement buy-and-hold "
                "si disponible, nomme le regime le plus et le moins performant (regime_ranking) avec leurs "
                "rendements moyens, et cite l'ampleur du pire episode de repli (top_drawdown_periods)."
            ),
        },
        "best_regime_comment": {
            "type": "object",
            "properties": {
                "claim": {"type": "string"},
                "evidence_trade_ids": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["claim", "evidence_trade_ids"],
            "description": (
                "Commentaire sur le regime le PLUS performant - CE REGIME EST DEJA DETERMINE (voir 'best_regime' "
                "dans le prompt), tu ne le choisis pas, tu le commentes uniquement. 'claim' DOIT inclure au moins "
                "un chiffre concret (taux de reussite, rendement moyen ou nombre de transactions) - jamais une "
                "simple reformulation generique comme 'ce regime semble etre le plus performant'."
            ),
        },
        "worst_regime_comment": {
            "type": "object",
            "properties": {
                "claim": {"type": "string"},
                "evidence_trade_ids": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["claim", "evidence_trade_ids"],
            "description": (
                "Commentaire sur le regime le MOINS performant - CE REGIME EST DEJA DETERMINE (voir 'worst_regime' "
                "dans le prompt), tu ne le choisis pas, tu le commentes uniquement. 'claim' DOIT inclure au moins "
                "un chiffre concret (taux de reussite, rendement moyen ou nombre de transactions) - jamais une "
                "simple reformulation generique comme 'ce regime semble etre le moins performant'."
            ),
        },
        "losing_trade_patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence_trade_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["claim", "evidence_trade_ids"],
            },
            "description": "Points communs observes entre les transactions perdantes.",
        },
        "caveats": {
            "type": "string",
            "description": "Limites explicites de cette analyse (taille d'echantillon, correlation vs causalite, etc.).",
        },
    },
    "required": ["summary", "best_regime_comment", "worst_regime_comment", "losing_trade_patterns", "caveats"],
}


PROMPT_TEMPLATE = """Tu es un assistant d'analyse de backtests financiers, dans un outil PEDAGOGIQUE (pas un conseiller en investissement, jamais un ordre a executer).

Regles STRICTES, a respecter absolument :
1. N'utilise QUE les faits fournis ci-dessous au format JSON. N'invente aucun chiffre, aucune date, aucune transaction qui n'y figure pas.
2. Chaque affirmation ("best_regime_comment", "worst_regime_comment", "losing_trade_patterns") DOIT citer au moins un `trade_id` reellement present dans la liste "trades" des faits fournis, dans le champ "evidence_trade_ids". Une affirmation sans preuve citee sera rejetee.
3. Reste descriptif, jamais causal de facon certaine : utilise "semble associe a", "coincide avec", jamais "cause" ou "explique de facon certaine" - tu observes des correlations sur un tres petit echantillon, pas une loi generale.
4. Dans "caveats", rappelle explicitement la taille de l'echantillon ({trade_count} transactions) et le fait qu'un backtest passe ne garantit rien sur l'avenir.
5. IMPORTANT (14/08/2026, corrige un echec reel observe) : le regime le PLUS performant est **"{best_regime}"** (rendement moyen {best_regime_return:+.2f}%) et le MOINS performant est **"{worst_regime}"** (rendement moyen {worst_regime_return:+.2f}%) - ces deux noms sont DEJA DETERMINES par calcul, tu ne les choisis pas et tu ne dois JAMAIS en mentionner un autre a leur place. "best_regime_comment" porte EXCLUSIVEMENT sur "{best_regime}", "worst_regime_comment" porte EXCLUSIVEMENT sur "{worst_regime}".
6. IMPORTANT - pour choisir "evidence_trade_ids", NE RECALCULE JAMAIS toi-meme a quel regime ou a quel resultat (gagnant/perdant) appartient une transaction en relisant la liste "trades" : utilise UNIQUEMENT les groupes deja calcules "trades_by_regime" (regime -> liste de trade_id), "winning_trade_ids" et "losing_trade_ids". Pour "best_regime_comment", "evidence_trade_ids" doit etre un sous-ensemble de trades_by_regime["{best_regime}"]. Pour "worst_regime_comment", un sous-ensemble de trades_by_regime["{worst_regime}"]. Pour "losing_trade_patterns", un sous-ensemble de "losing_trade_ids".
7. Reponds UNIQUEMENT en JSON valide, respectant strictement le schema demande. Aucun texte hors du JSON.
8. "summary" NE DOIT JAMAIS se contenter de reformuler le titre (ex. "Analyse de backtest de X sur Y du ... au ...") - c'est INTERDIT et sera considere comme un echec. "summary" DOIT contenir, en 2-4 phrases : (a) le rendement total obtenu, chiffre precis tire de "aggregate_stats" (cle "Return [%]"), compare au rendement buy-and-hold si "Buy & Hold Return [%]" est present ; (b) "{best_regime}" comme regime le plus performant ({best_regime_return:+.2f}%) et "{worst_regime}" comme le moins performant ({worst_regime_return:+.2f}%) - ne cite JAMAIS un autre regime a leur place ; (c) l'ampleur (en %) du pire episode de repli d'apres "top_drawdown_periods", en precisant s'il etait encore en cours a la fin de la periode (champ "end" a null).
9. IMPORTANT (16/08/2026, corrige un echec reel observe) : le "claim" de "best_regime_comment" et de "worst_regime_comment" NE DOIT JAMAIS se limiter a une reformulation generique du type "ce regime semble etre le plus/moins performant" - c'est INTERDIT et sera considere comme un echec, EXACTEMENT comme pour "summary" (regle 8). Chaque "claim" DOIT citer au moins un chiffre precis tire de "regime_performance" pour le regime concerne (son "avg_return_pct", son "win_rate_pct", ou son "count") en plus des transactions citees dans "evidence_trade_ids".

Faits (strategie "{strategy_name}" sur {ticker}, du {period_start} au {period_end}) :
{facts_json}
"""


@dataclass
class AnalysisReport:
    markdown: str
    llm_data: dict
    citation_warnings: list[str]
    model: str
    from_cache: bool
    low_sample_warning: bool


def _best_worst_regime(facts: dict) -> tuple[dict, dict]:
    """Determine par CODE (jamais par le LLM) quel regime est le meilleur et
    lequel est le pire, a partir du classement deja calcule
    `facts["regime_ranking"]` (trie du meilleur au pire, voir
    `quant_facts.rank_regimes_by_performance`). 14/08/2026 : c'est le coeur
    du correctif suite a un cas reel observe ou llama3.1 avait correctement
    identifie le meilleur regime mais mal etiquete le pire (confondu avec un
    troisieme regime intermediaire) - en retirant au modele la possibilite
    de CHOISIR quel regime est "best"/"worst", cette classe d'erreur devient
    structurellement impossible cote LLM (le garde-fou de validation reste
    en place quand meme, au cas ou le modele l'ignorerait).

    Cas limite : un seul regime avec des transactions -> best == worst (le
    prompt le presentera comme tel, ce qui est correct). Aucun regime avec
    de transactions (ne devrait pas arriver si trade_count > 0) -> regime a
    None, gere par les appelants."""
    ranking = facts.get("regime_ranking") or []
    if not ranking:
        empty = {"regime": None, "avg_return_pct": None, "count": 0}
        return empty, empty
    return ranking[0], ranking[-1]


def build_prompt(strategy_name: str, ticker: str, period_start: date, period_end: date, facts: dict) -> str:
    best, worst = _best_worst_regime(facts)
    return PROMPT_TEMPLATE.format(
        strategy_name=strategy_name,
        ticker=ticker,
        period_start=period_start,
        period_end=period_end,
        trade_count=facts["trade_count"],
        best_regime=best["regime"] or "n/d",
        best_regime_return=best["avg_return_pct"] or 0.0,
        worst_regime=worst["regime"] or "n/d",
        worst_regime_return=worst["avg_return_pct"] or 0.0,
        facts_json=json.dumps(facts, ensure_ascii=False, indent=2),
    )


def _validate_citations(llm_data: dict, facts: dict) -> list[str]:
    """Verifie que CHAQUE trade_id cite par le LLM existe reellement dans
    les faits fournis (garde-fou anti-hallucination), PUIS que l'affirmation
    qui l'entoure est bien COHERENTE avec ce que dit ce trade precis - pas
    seulement qu'il existe.

    14/08/2026 : `best_regime_comment` et `worst_regime_comment` sont
    desormais des champs FIXES dont le regime cible est determine par
    `_best_worst_regime()` (code), plus un champ libre choisi par le LLM
    (voir historique : le modele pouvait citer des transactions reelles du
    bon regime tout en se trompant sur QUEL regime etait le "pire"). Cette
    fonction verifie ici que chaque champ ne cite que des transactions
    appartenant reellement au regime qui lui est assigne - un filet de
    securite si le modele ignore quand meme la consigne. `losing_trade_patterns`
    garde sa verification is_win inchangee."""
    valid_ids = {t["trade_id"] for t in facts["trades"]}
    trades_by_id = {t["trade_id"]: t for t in facts["trades"]}
    trades_by_regime = facts.get("trades_by_regime", {})
    warnings: list[str] = []

    def _check_citations(section: str, item: dict, allowed_ids: set | None, regime_label: str | None) -> set:
        cited = set(item.get("evidence_trade_ids", []))
        invalid = cited - valid_ids
        if invalid:
            warnings.append(
                f"Affirmation non verifiee dans '{section}' : cite les transactions {sorted(invalid)} "
                f"qui n'existent pas dans les donnees fournies - claim : {item.get('claim', '')!r}"
            )
        if not cited:
            warnings.append(
                f"Affirmation sans transaction citee dans '{section}' (ignore la regle de citation obligatoire) - "
                f"claim : {item.get('claim', '')!r}"
            )

        valid_cited = cited & valid_ids

        if allowed_ids is not None:
            mismatched = valid_cited - allowed_ids
            if mismatched:
                warnings.append(
                    f"Incoherence dans '{section}' : les transactions {sorted(mismatched)} citees "
                    f"n'appartiennent PAS au regime '{regime_label}' - claim : {item.get('claim', '')!r}"
                )

        return valid_cited

    best, worst = _best_worst_regime(facts)

    if best["regime"]:
        allowed = set(trades_by_regime.get(best["regime"], []))
        _check_citations("best_regime_comment", llm_data.get("best_regime_comment") or {}, allowed, best["regime"])

    if worst["regime"]:
        allowed = set(trades_by_regime.get(worst["regime"], []))
        _check_citations("worst_regime_comment", llm_data.get("worst_regime_comment") or {}, allowed, worst["regime"])

    for item in llm_data.get("losing_trade_patterns", []):
        valid_cited = _check_citations("losing_trade_patterns", item, None, None)
        winners_cited = [tid for tid in valid_cited if trades_by_id[tid]["is_win"]]
        if winners_cited:
            warnings.append(
                f"Incoherence dans 'losing_trade_patterns' : les transactions {sorted(winners_cited)} "
                f"citees sont en realite GAGNANTES, pas perdantes - claim : {item.get('claim', '')!r}"
            )

    return warnings


def _validate_summary(summary: str) -> list[str]:
    """Detecte un resume "paresseux" (14/08/2026 - observe en usage reel
    avec llama3.1 : "Analyse de backtest de la strategie 'sma_cross' sur
    ABI.BR du 2025-01-01 au 2026-08-16", une pure reformulation du titre,
    zero chiffre). L'instruction du prompt (regle 8) demande explicitement
    des chiffres precis - ce garde-fou verifie mecaniquement qu'au moins un
    signe "%" est present, sans essayer de comprendre le texte (impossible
    de verifier l'EXACTITUDE des chiffres cites sans reparser le langage
    naturel - seule leur PRESENCE est verifiee ici, contrairement aux
    citations de trade_id qui elles sont entierement verifiables)."""
    if "%" not in summary:
        return [
            "Le resume ('summary') ne cite aucun pourcentage alors que la consigne l'exige explicitement "
            "(rendement, regime, drawdown) - probablement un resume generique peu informatif, a lire avec prudence."
        ]
    return []


def _validate_regime_comment(item: dict, section: str) -> list[str]:
    """Meme logique que `_validate_summary()`, appliquee cette fois aux deux
    champs fixes du regime (16/08/2026) : en usage reel, une fois le bug de
    mauvais etiquetage corrige (voir `_best_worst_regime`), le modele s'est
    mis a produire des "claim" corrects mais vides de contenu - "Le regime
    'moyenne' semble etre le plus performant." - sans aucun chiffre a
    l'appui, alors que la regle 9 du prompt l'exige explicitement. Verifie
    mecaniquement la PRESENCE d'au moins un chiffre dans le texte (comme
    pour le resume, pas son exactitude - impossible a verifier sans reparser
    du langage naturel)."""
    claim = item.get("claim", "")
    if not any(ch.isdigit() for ch in claim):
        return [
            f"Le commentaire '{section}' ne cite aucun chiffre concret (taux de reussite, rendement moyen, "
            f"nombre de transactions) alors que la consigne l'exige explicitement - probablement une observation "
            f"generique peu informative, a lire avec prudence."
        ]
    return []


def render_markdown(
    strategy_name: str,
    ticker: str,
    period_start: date,
    period_end: date,
    facts: dict,
    llm_data: dict,
    citation_warnings: list[str],
    model: str,
    from_cache: bool,
    low_sample_warning: bool,
) -> str:
    lines = [
        f"# Analyse de backtest - {ticker} - {strategy_name}",
        "",
        f"Periode : {period_start} au {period_end}  ",
        f"Transactions : {facts['trade_count']}  ",
        f"Modele : {model}{' (reponse en cache)' if from_cache else ''}",
        "",
        "> Rapport genere automatiquement par un LLM local (Ollama), a partir de faits precalcules en Python "
        "pur (jamais decouverts par le modele lui-meme). Ne constitue en aucun cas un conseil en investissement "
        "ni une prediction - un backtest passe ne garantit rien sur l'avenir.",
        "",
    ]

    if low_sample_warning:
        lines += [
            f"**⚠ Échantillon faible ({facts['trade_count']} transactions, seuil recommande : "
            f"{MIN_TRADES_FOR_NARRATIVE}) - les observations ci-dessous sont exploratoires, pas des conclusions.**",
            "",
        ]

    lines += ["## Résumé", "", llm_data.get("summary", "(aucun resume genere)"), ""]

    lines += ["## Observations par régime de volatilité", ""]

    if facts.get("regime_ranking"):
        ranking_str = " > ".join(
            f"{r['regime']} ({r['avg_return_pct']:+.2f}%, {r['count']} transaction{'s' if r['count'] > 1 else ''})"
            for r in facts["regime_ranking"]
        )
        lines += [
            f"**Classement réel par rendement moyen (calculé, pas généré par le modèle) : {ranking_str}.**",
            "Compare toujours les observations ci-dessous à ce classement avant de les prendre pour argent comptant.",
            "",
        ]

    best, worst = _best_worst_regime(facts)
    if best["regime"]:
        best_comment = llm_data.get("best_regime_comment") or {}
        best_ids = ", ".join(f"#{i}" for i in best_comment.get("evidence_trade_ids", []))
        lines.append(f"**Meilleur regime : {best['regime']} ({best['avg_return_pct']:+.2f}%)**")
        lines.append(f"- {best_comment.get('claim') or '(aucun commentaire genere)'} _(transactions {best_ids})_")
        lines.append("")

        worst_comment = llm_data.get("worst_regime_comment") or {}
        worst_ids = ", ".join(f"#{i}" for i in worst_comment.get("evidence_trade_ids", []))
        lines.append(f"**Pire regime : {worst['regime']} ({worst['avg_return_pct']:+.2f}%)**")
        lines.append(f"- {worst_comment.get('claim') or '(aucun commentaire genere)'} _(transactions {worst_ids})_")
    else:
        lines.append("_Aucune observation generee (aucun regime avec transactions)._")
    lines.append("")

    lines += ["## Points communs entre transactions perdantes", ""]
    if llm_data.get("losing_trade_patterns"):
        for item in llm_data["losing_trade_patterns"]:
            ids = ", ".join(f"#{i}" for i in item.get("evidence_trade_ids", []))
            lines.append(f"- {item.get('claim', '')} _(transactions {ids})_")
    else:
        lines.append("_Aucune observation generee._")
    lines.append("")

    lines += ["## Limites de cette analyse", "", llm_data.get("caveats", ""), ""]

    if citation_warnings:
        lines += ["## ⚠ Avertissements de verification (généré automatiquement)", ""]
        lines += [f"- {w}" for w in citation_warnings]
        lines.append("")

    lines += [
        "## Faits bruts utilisés (référence)",
        "",
        "Performance par régime de volatilité :",
        "",
        "| Régime | Transactions | Taux de réussite | Rendement moyen |",
        "|---|---|---|---|",
    ]
    for regime, stats in facts["regime_performance"].items():
        wr = f"{stats['win_rate_pct']}%" if stats["win_rate_pct"] is not None else "n/d"
        ret = f"{stats['avg_return_pct']}%" if stats["avg_return_pct"] is not None else "n/d"
        lines.append(f"| {regime} | {stats['count']} | {wr} | {ret} |")
    lines.append("")

    if facts["top_drawdown_periods"]:
        lines += ["Pires épisodes de repli :", ""]
        for ep in facts["top_drawdown_periods"]:
            lines.append(f"- {ep['start']} → {ep['trough']} → {ep['end'] or '(en cours en fin de période)'} : -{ep['depth_pct']}%")
        lines.append("")

    return "\n".join(lines)


def analyze(
    provider: LLMProvider,
    strategy_name: str,
    ticker: str,
    period_start: date,
    period_end: date,
    facts: dict,
    *,
    use_cache: bool = True,
) -> AnalysisReport:
    low_sample_warning = facts["trade_count"] < MIN_TRADES_FOR_NARRATIVE

    prompt = build_prompt(strategy_name, ticker, period_start, period_end, facts)
    response = provider.complete(prompt, json_schema=RESPONSE_SCHEMA, use_cache=use_cache)
    citation_warnings = _validate_citations(response.data, facts)
    citation_warnings += _validate_summary(response.data.get("summary", ""))
    citation_warnings += _validate_regime_comment(response.data.get("best_regime_comment") or {}, "best_regime_comment")
    citation_warnings += _validate_regime_comment(response.data.get("worst_regime_comment") or {}, "worst_regime_comment")

    markdown = render_markdown(
        strategy_name,
        ticker,
        period_start,
        period_end,
        facts,
        response.data,
        citation_warnings,
        response.model,
        response.from_cache,
        low_sample_warning,
    )

    return AnalysisReport(
        markdown=markdown,
        llm_data=response.data,
        citation_warnings=citation_warnings,
        model=response.model,
        from_cache=response.from_cache,
        low_sample_warning=low_sample_warning,
    )
