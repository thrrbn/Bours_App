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
            "description": "2-4 phrases resumant le comportement general de la strategie sur cette periode.",
        },
        "regime_findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "regime": {"type": "string", "enum": ["faible", "moyenne", "elevee"]},
                    "evidence_trade_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["claim", "evidence_trade_ids"],
            },
            "description": "Observations liees aux regimes de volatilite (regime_performance dans les faits fournis).",
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
    "required": ["summary", "regime_findings", "losing_trade_patterns", "caveats"],
}


PROMPT_TEMPLATE = """Tu es un assistant d'analyse de backtests financiers, dans un outil PEDAGOGIQUE (pas un conseiller en investissement, jamais un ordre a executer).

Regles STRICTES, a respecter absolument :
1. N'utilise QUE les faits fournis ci-dessous au format JSON. N'invente aucun chiffre, aucune date, aucune transaction qui n'y figure pas.
2. Chaque affirmation dans "regime_findings" et "losing_trade_patterns" DOIT citer au moins un `trade_id` reellement present dans la liste "trades" des faits fournis, dans le champ "evidence_trade_ids". Une affirmation sans preuve citee sera rejetee.
3. Reste descriptif, jamais causal de facon certaine : utilise "semble associe a", "coincide avec", jamais "cause" ou "explique de facon certaine" - tu observes des correlations sur un tres petit echantillon, pas une loi generale.
4. Dans "caveats", rappelle explicitement la taille de l'echantillon ({trade_count} transactions) et le fait qu'un backtest passe ne garantit rien sur l'avenir.
5. Reponds UNIQUEMENT en JSON valide, respectant strictement le schema demande. Aucun texte hors du JSON.

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


def build_prompt(strategy_name: str, ticker: str, period_start: date, period_end: date, facts: dict) -> str:
    return PROMPT_TEMPLATE.format(
        strategy_name=strategy_name,
        ticker=ticker,
        period_start=period_start,
        period_end=period_end,
        trade_count=facts["trade_count"],
        facts_json=json.dumps(facts, ensure_ascii=False, indent=2),
    )


def _validate_citations(llm_data: dict, facts: dict) -> list[str]:
    """Verifie que CHAQUE trade_id cite par le LLM existe reellement dans
    les faits fournis - un garde-fou simple mais direct contre
    l'hallucination : si le modele invente un trade_id qui n'existe pas,
    l'affirmation correspondante est signalee comme non fiable dans le
    rapport final plutot que d'etre presentee comme une conclusion valide."""
    valid_ids = {t["trade_id"] for t in facts["trades"]}
    warnings = []

    for section in ("regime_findings", "losing_trade_patterns"):
        for item in llm_data.get(section, []):
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

    return warnings


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
    if llm_data.get("regime_findings"):
        for item in llm_data["regime_findings"]:
            ids = ", ".join(f"#{i}" for i in item.get("evidence_trade_ids", []))
            lines.append(f"- {item.get('claim', '')} _(transactions {ids})_")
    else:
        lines.append("_Aucune observation generee._")
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
