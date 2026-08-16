"""
Point d'entree en ligne de commande (14/08/2026). Usage : voir README.md.

Exemple :
    python cli.py --url http://192.168.1.50:8000 --ticker MC.PA \\
        --strategy rsi_mean_reversion --start 2025-01-01 --end 2026-08-01
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from analyst import analyze
from api_client import ApiClientError, BourseApiClient
from backtest_runner import BacktestRunnerError, run_local_backtest
from llm_provider import LLMProviderError, OllamaProvider
from quant_facts import build_facts
from strategies import SUPPORTED_STRATEGIES


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyste LLM local (Ollama) pour un backtest de Bourse Assistant - outil autonome, "
        "ne modifie jamais l'application ni le NAS (voir README.md)."
    )
    parser.add_argument("--url", required=True, help="URL de base de l'API (ex: http://192.168.1.50:8000)")
    parser.add_argument("--ticker", required=True, help="Ticker deja suivi dans l'application (ex: MC.PA)")
    parser.add_argument("--strategy", required=True, choices=SUPPORTED_STRATEGIES)
    parser.add_argument("--start", required=True, help="Date de debut (AAAA-MM-JJ)")
    parser.add_argument("--end", required=True, help="Date de fin (AAAA-MM-JJ)")
    parser.add_argument("--model", default="llama3.1", help="Modele Ollama a utiliser (defaut: llama3.1)")
    parser.add_argument("--ollama-url", default=None, help="URL du serveur Ollama (defaut: http://localhost:11434)")
    parser.add_argument("--no-cache", action="store_true", help="Ignore le cache disque, force un nouvel appel LLM")
    parser.add_argument("--out", default=None, help="Fichier de sortie .md (defaut: affiche dans le terminal)")
    args = parser.parse_args()

    period_start = date.fromisoformat(args.start)
    period_end = date.fromisoformat(args.end)

    print(f"[1/4] Recuperation des prix pour {args.ticker} depuis {args.url}...", file=sys.stderr)
    try:
        client = BourseApiClient(args.url)
        asset = client.resolve_ticker(args.ticker)
        price_df = client.fetch_price_history(asset["id"], period_start, period_end)
    except ApiClientError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    print(f"[2/4] Backtest local ({args.strategy}, {len(price_df)} bougies)...", file=sys.stderr)
    try:
        result = run_local_backtest(price_df, args.strategy)
    except BacktestRunnerError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    print(f"[3/4] Calcul des faits quantitatifs ({len(result.trades)} transactions)...", file=sys.stderr)
    facts = build_facts(result.price_df, result.trades, result.equity_curve, result.stats)

    print(f"[4/4] Analyse par le modele local '{args.model}' (peut prendre plusieurs minutes)...", file=sys.stderr)
    provider = OllamaProvider(model=args.model, base_url=args.ollama_url)
    try:
        report = analyze(
            provider,
            args.strategy,
            asset["ticker"],
            period_start,
            period_end,
            facts,
            use_cache=not args.no_cache,
        )
    except LLMProviderError as exc:
        print(f"Erreur LLM : {exc}", file=sys.stderr)
        return 1

    if report.citation_warnings:
        print(f"⚠ {len(report.citation_warnings)} affirmation(s) non verifiee(s) - voir le rapport.", file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report.markdown)
        print(f"Rapport ecrit dans {args.out}", file=sys.stderr)
    else:
        print(report.markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
