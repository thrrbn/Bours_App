"""
Faits quantitatifs precalcules, SANS LLM (14/08/2026) - decision de
conception centrale de cet outil (voir conversation du 14/08/2026 et
README.md) : tout ce qui peut etre calcule exactement et de facon
reproductible par du Python pur DOIT l'etre ici, jamais "decouvert" par le
LLM a partir de donnees brutes. Le role du LLM (voir analyst.py) se limite
ensuite a METTRE EN RECIT des faits deja etablis, avec obligation de citer
l'identifiant de transaction (`trade_id`, voir `build_facts()`) pour toute
affirmation - ce qui permet une verification post-hoc (voir
analyst.py::_validate_citations).

Toutes les fonctions ci-dessous sont PURES (aucun IO, aucun appel reseau) -
meme philosophie de test que le reste du projet principal (voir
backend/tests/conftest.py : "les tests essentiels ciblent les modules PURS").
"""
from __future__ import annotations

import numpy as np
import pandas as pd

REGIME_LABELS = ("faible", "moyenne", "elevee")


def compute_volatility_regimes(price_df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Volatilite realisee (ecart-type des rendements journaliers, fenetre
    glissante, annualisee) decoupee en tertiles sur TOUTE la periode testee
    -> une etiquette 'faible'/'moyenne'/'elevee' par date. Les tertiles sont
    calcules sur la periode elle-meme (pas de reference externe) : "eleve"
    signifie donc "eleve par rapport au reste de CETTE periode testee", pas
    un seuil absolu universel - a rappeler dans le rapport final."""
    returns = price_df["Close"].pct_change()
    rolling_vol = returns.rolling(window).std() * np.sqrt(252)
    valid = rolling_vol.dropna()
    if len(valid) < 3:
        return pd.Series("moyenne", index=price_df.index)

    q1, q2 = valid.quantile([1 / 3, 2 / 3])

    def _label(v):
        if pd.isna(v):
            return "moyenne"
        if v <= q1:
            return "faible"
        if v <= q2:
            return "moyenne"
        return "elevee"

    return rolling_vol.apply(_label).reindex(price_df.index).fillna("moyenne")


def build_trade_index(trades: pd.DataFrame, regimes: pd.Series) -> pd.DataFrame:
    """Une ligne par transaction, avec un `trade_id` stable (1-indexe, ordre
    chronologique) - c'est CE tableau que le LLM doit citer par `trade_id`
    dans ses affirmations (voir analyst.py). Le regime associe a une
    transaction est celui du jour de son ENTREE (le contexte qui a motive
    le trade, pas la moyenne sur toute sa duree)."""
    if trades.empty:
        return pd.DataFrame(
            columns=["trade_id", "entry_date", "exit_date", "duration_days", "pnl", "return_pct", "is_win", "regime"]
        )

    rows = []
    for i, (_, trade) in enumerate(trades.iterrows(), start=1):
        entry_date = trade["EntryTime"]
        regime_value = regimes.asof(entry_date)
        regime = regime_value if isinstance(regime_value, str) else "moyenne"
        duration = trade["Duration"]
        duration_days = duration.total_seconds() / 86400 if hasattr(duration, "total_seconds") else None
        rows.append(
            {
                "trade_id": i,
                "entry_date": str(pd.Timestamp(entry_date).date()),
                "exit_date": str(pd.Timestamp(trade["ExitTime"]).date()),
                "duration_days": round(duration_days, 1) if duration_days is not None else None,
                "pnl": round(float(trade["PnL"]), 2),
                "return_pct": round(float(trade["ReturnPct"]) * 100, 2),
                "is_win": bool(trade["PnL"] > 0),
                "regime": regime,
            }
        )
    return pd.DataFrame(rows)


def regime_performance(trade_index: pd.DataFrame) -> dict:
    """Performance agregee par regime de volatilite - repond a "la strategie
    casse-t-elle plutot en periode calme ou agitee ?". Chaque bucket
    rapporte son propre `count` : a ne jamais lire sans regarder ce compte
    (meme principe que le badge de confiance du scorecard de l'application
    principale - un bucket a 2 transactions n'est pas une tendance)."""
    result = {}
    for label in REGIME_LABELS:
        subset = trade_index[trade_index["regime"] == label]
        count = len(subset)
        result[label] = {
            "count": count,
            "win_rate_pct": round(100 * subset["is_win"].mean(), 1) if count else None,
            "avg_return_pct": round(subset["return_pct"].mean(), 2) if count else None,
            "total_pnl": round(subset["pnl"].sum(), 2) if count else None,
        }
    return result


def characterize_losing_trades(trade_index: pd.DataFrame) -> dict:
    """Compare les transactions perdantes aux gagnantes sur des attributs
    simples et objectifs (duree, jour de la semaine d'entree) - jamais une
    causalite, juste des correlations descriptives que le LLM devra nuancer,
    pas affirmer comme des lois."""
    if trade_index.empty:
        return {"count_losers": 0, "count_winners": 0}

    losers = trade_index[~trade_index["is_win"]]
    winners = trade_index[trade_index["is_win"]]

    def _weekday_counts(df: pd.DataFrame) -> dict:
        if df.empty:
            return {}
        weekdays = pd.to_datetime(df["entry_date"]).dt.day_name()
        return weekdays.value_counts().to_dict()

    return {
        "count_losers": len(losers),
        "count_winners": len(winners),
        "avg_duration_days_losers": round(losers["duration_days"].mean(), 1) if len(losers) else None,
        "avg_duration_days_winners": round(winners["duration_days"].mean(), 1) if len(winners) else None,
        "entry_weekday_counts_losers": _weekday_counts(losers),
        "worst_trade": losers.loc[losers["pnl"].idxmin()].to_dict() if len(losers) else None,
        "best_trade": winners.loc[winners["pnl"].idxmax()].to_dict() if len(winners) else None,
    }


def top_drawdown_periods(equity_curve: pd.DataFrame, top_n: int = 3) -> list[dict]:
    """Identifie les N pires episodes de repli (sommet -> creux -> retour au
    sommet precedent) a partir de la courbe de capital - calcul exact
    (pas d'estimation), utilise le DrawdownPct deja fourni par
    backtesting.py dans `_equity_curve` quand disponible.

    Convention (verifiee empiriquement, 14/08/2026) : backtesting.py stocke
    DrawdownPct comme une magnitude POSITIVE (0 = au sommet, 0.20 = -20%
    depuis le dernier sommet) - PAS une valeur negative. Meme convention que
    le reste de ce projet (voir kernc_engine.py::run_kernc_backtest,
    "max_drawdown": abs(...)/100) : `depth_pct` ci-dessous est donc un
    pourcentage POSITIF representant l'ampleur de la perte, jamais un nombre
    negatif a interpreter comme un gain."""
    if equity_curve.empty or "DrawdownPct" not in equity_curve.columns:
        return []

    dd = equity_curve["DrawdownPct"]
    episodes = []
    in_drawdown = False
    start_idx = None
    trough_idx = None
    trough_value = 0.0

    for idx, value in dd.items():
        value = float(value) if not pd.isna(value) else 0.0
        if value > 0 and not in_drawdown:
            in_drawdown = True
            start_idx = idx
            trough_idx = idx
            trough_value = value
        elif value > 0 and in_drawdown:
            if value > trough_value:
                trough_value = value
                trough_idx = idx
        elif value <= 0 and in_drawdown:
            episodes.append(
                {
                    "start": str(pd.Timestamp(start_idx).date()),
                    "trough": str(pd.Timestamp(trough_idx).date()),
                    "end": str(pd.Timestamp(idx).date()),
                    "depth_pct": round(trough_value * 100, 2),
                }
            )
            in_drawdown = False

    if in_drawdown:
        episodes.append(
            {
                "start": str(pd.Timestamp(start_idx).date()),
                "trough": str(pd.Timestamp(trough_idx).date()),
                "end": None,
                "depth_pct": round(trough_value * 100, 2),
            }
        )

    episodes.sort(key=lambda e: e["depth_pct"], reverse=True)
    return episodes[:top_n]


def build_facts(price_df: pd.DataFrame, trades: pd.DataFrame, equity_curve: pd.DataFrame, stats: dict) -> dict:
    """Assemble tous les faits ci-dessus en un seul dict JSON-serialisable -
    c'est EXACTEMENT ce dict, et rien d'autre, qui est fourni au LLM (voir
    analyst.py::build_prompt). Aucune donnee brute (le DataFrame de prix
    complet, par exemple) n'est envoyee telle quelle : uniquement des faits
    deja resumes."""
    regimes = compute_volatility_regimes(price_df)
    trade_index = build_trade_index(trades, regimes)

    return {
        "sign_conventions": (
            "Dans 'aggregate_stats', les pourcentages de perte (ex. 'Max. Drawdown [%]') sont NEGATIFS "
            "(convention brute de backtesting.py). Dans 'top_drawdown_periods', 'depth_pct' est une "
            "magnitude POSITIVE (20.0 signifie une perte de 20%, jamais un gain). Ne pas confondre les deux."
        ),
        "aggregate_stats": stats,
        "trade_count": len(trade_index),
        "trades": trade_index.to_dict(orient="records"),
        "regime_performance": regime_performance(trade_index),
        "losing_trades_profile": characterize_losing_trades(trade_index),
        "top_drawdown_periods": top_drawdown_periods(equity_curve),
    }
