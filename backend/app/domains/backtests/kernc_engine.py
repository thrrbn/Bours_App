"""
Integration de la librairie backtesting.py (github.com/kernc/backtesting.py,
MIT) comme SECOND moteur de backtest, en complement de service.py::evaluate_signals
(Etape 18) - PAS en remplacement (decision produit du 31/07/2026, voir
docs/STACK.md pour la discussion complete).

Difference de philosophie entre les deux moteurs :
- evaluate_signals() (moteur "interne") rejoue des signaux DEJA calcules et
  stockes (table signals), et mesure des metriques analytiques simplifiees
  (precision, win rate, Sharpe/Calmar non annualises) SANS simuler de vrai
  cash/positions/ordres - un signal est juste compare a un rendement futur.
- backtesting.py (ce module) simule un VRAI trading bar-par-bar sur les
  cours OHLC reels : cash, commission, ordres, equity curve complete - et
  calcule des metriques plus riches et standards du secteur (Sortino,
  Exposure Time, SQN, Best/Worst Trade, Alpha/Beta vs Buy & Hold...).

Les deux moteurs ecrivent dans les MEMES tables (backtest_runs / backtest_results,
voir models.py) - engine_version et strategy_name permettent de les
distinguer et de les comparer cote a cote pour un meme actif/periode (voir
router.py: POST /run vs POST /run-kernc).

Strategies disponibles (STRATEGY_* / ALL_STRATEGIES) :
- signal_replay (SignalReplayStrategy) : rejoue nos PROPRES signaux stockes
  (moteur de regles + apercu ML) comme des ordres reels - la comparaison la
  plus directe avec ce que "suivre nos signaux" aurait vraiment produit en
  cash, frais et slippage inclus.
- sma_cross (SmaCrossStrategy) et buy_and_hold (BuyAndHoldStrategy) :
  benchmarks classiques (repris de l'exemple du README de backtesting.py)
  pour situer nos signaux par rapport a des strategies simples et connues
  du secteur - demande explicite de l'utilisateur (31/07/2026).

Limite assumee : backtesting.py ne fait pas de walk-forward par construction
(un parametre "entraine" sur toute la serie verrait le futur). Ici ce risque
n'existe pas : signal_replay rejoue des signaux DEJA pre-calcules par le
moteur interne, qui lui respecte le walk-forward (voir
signals/training.py::chronological_split) ; sma_cross/buy_and_hold n'ont de
toute facon aucun parametre entraine sur des donnees futures (moyennes
mobiles a fenetre fixe, pas d'optimisation).
"""
import uuid
from datetime import date

import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_data.models import PriceBar
from app.domains.signals.models import Signal

STRATEGY_SIGNAL_REPLAY = "signal_replay"
STRATEGY_SMA_CROSS = "sma_cross"
STRATEGY_BUY_AND_HOLD = "buy_and_hold"

ALL_STRATEGIES = (STRATEGY_SIGNAL_REPLAY, STRATEGY_SMA_CROSS, STRATEGY_BUY_AND_HOLD)

# Meme convention de sens que evaluate_signals() dans service.py : un signal
# "achat_speculatif"/"surveillance" est haussier, "prudence"/"vente_defensive"
# est baissier, "neutre" est ignore.
_BULLISH_SIGNALS = ("achat_speculatif", "surveillance")
_BEARISH_SIGNALS = ("prudence", "vente_defensive")

# Cle de chaque statistique de bt.run() qu'on conserve dans extra_metrics
# (on exclut volontairement Start/End/Duration - deja dans backtest_runs -
# et _strategy/_equity_curve/_trades qui ne sont pas des scalaires
# serialisables en JSON).
_EXTRA_STATS_KEYS = (
    "Exposure Time [%]",
    "Equity Final [$]",
    "Equity Peak [$]",
    "Commissions [$]",
    "Return [%]",
    "Buy & Hold Return [%]",
    "Return (Ann.) [%]",
    "Volatility (Ann.) [%]",
    "CAGR [%]",
    "Sortino Ratio",
    "Alpha [%]",
    "Beta",
    "Avg. Drawdown [%]",
    "Max. Drawdown Duration",
    "Avg. Drawdown Duration",
    "Best Trade [%]",
    "Worst Trade [%]",
    "Avg. Trade [%]",
    "Max. Trade Duration",
    "Avg. Trade Duration",
    "Expectancy [%]",
    "SQN",
    "Kelly Criterion",
)


def _num(stats: "pd.Series", key: str) -> float | None:
    """Extrait un scalaire numerique d'une Stats de backtesting.py, en geran
    proprement l'absence de cle et les NaN (ex: Sharpe indefini si aucun
    trade) - jamais d'exception, juste None."""
    if key not in stats:
        return None
    value = stats[key]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "total_seconds"):  # pandas Timedelta (durees de drawdown/trade)
        return round(value.total_seconds() / 86400, 2)  # en jours
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stats_to_extra_metrics(stats: "pd.Series") -> dict:
    extra = {}
    for key in _EXTRA_STATS_KEYS:
        value = _num(stats, key)
        if value is not None:
            extra[key] = value
    return extra


async def _load_price_dataframe(
    db: AsyncSession, asset_id: uuid.UUID, period_start: date, period_end: date
) -> pd.DataFrame:
    """
    Construit un DataFrame OHLCV compatible backtesting.py (colonnes Open/
    High/Low/Close/Volume, index datetime croissant) a partir de price_bars.

    Etape 19 (deja appliquee ailleurs, voir backtests/service.py::_return_price
    et market_data/providers/yahoo_finance.py) : le rendement de backtesting
    doit se baser sur le cours AJUSTE des dividendes/splits, pas le cours
    brut. On ne stocke que adjusted_close (pas d'Open/High/Low ajustes) -
    on retraite donc Open/High/Low par le meme facteur multiplicatif
    (adjusted_close / close) que celui implicitement applique a Close, pour
    garder des chandeliers coherents (Open/High/Low/Close du meme ordre de
    grandeur) plutot que de melanger un Close ajuste avec un O/H/L brut.
    """
    stmt = (
        select(PriceBar)
        .where(
            PriceBar.asset_id == asset_id,
            PriceBar.trade_date >= period_start,
            PriceBar.trade_date <= period_end,
        )
        .order_by(PriceBar.trade_date.asc())
    )
    result = await db.execute(stmt)
    bars = list(result.scalars().all())
    if len(bars) < 5:  # backtesting.py a besoin d'un minimum de bougies (SMA 20, etc.)
        return pd.DataFrame()

    rows = []
    for bar in bars:
        close = float(bar.close)
        adjusted_close = float(bar.adjusted_close) if bar.adjusted_close is not None else close
        factor = (adjusted_close / close) if close else 1.0
        rows.append(
            {
                "date": bar.trade_date,
                "Open": float(bar.open) * factor,
                "High": float(bar.high) * factor,
                "Low": float(bar.low) * factor,
                "Close": adjusted_close,
                "Volume": bar.volume or 0,
            }
        )
    df = pd.DataFrame(rows).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df


async def _load_signal_map(
    db: AsyncSession, asset_id: uuid.UUID, horizon: str, period_start: date, period_end: date
) -> dict:
    """{date: final_signal} - un signal par jour (le plus recent si plusieurs
    calculs le meme jour, gere par l'ordre croissant + ecrasement dict)."""
    stmt = (
        select(Signal)
        .where(
            Signal.asset_id == asset_id,
            Signal.horizon == horizon,
            Signal.computed_at >= period_start,
            Signal.computed_at <= period_end,
        )
        .order_by(Signal.computed_at.asc())
    )
    result = await db.execute(stmt)
    signals = list(result.scalars().all())
    return {s.computed_at.date(): s.final_signal for s in signals}


def _sma(values, n):
    return pd.Series(values).rolling(n).mean()


class SignalReplayStrategy(Strategy):
    """
    Rejoue nos propres signaux stockes comme des ordres reels : passe a 100%
    long quand le dernier signal connu est haussier (achat_speculatif /
    surveillance), solde la position quand il devient baissier (prudence /
    vente_defensive). Sur 'neutre' ou en l'absence de signal connu ce
    jour-la, ne fait rien (repli sur le dernier signal connu - un
    investisseur qui n'a pas de nouvelle information ne change pas de
    position sans raison).

    signal_map est injecte via bt.run(signal_map=...) (backtesting.py
    reconnait tout attribut de classe passe en kwarg a run() et l'affecte a
    l'instance avant init()) plutot que par mutation de l'attribut de classe
    - evite tout partage d'etat entre deux runs successifs.
    """

    signal_map: dict = {}

    def init(self):
        codes = []
        last = "neutre"
        for d in self.data.index:
            key = d.date() if hasattr(d, "date") else d
            last = self.signal_map.get(key, last)
            codes.append(last)
        self._codes = codes

    def next(self):
        code = self._codes[len(self.data) - 1]
        if code in _BULLISH_SIGNALS and not self.position:
            self.buy()
        elif code in _BEARISH_SIGNALS and self.position:
            self.position.close()


class SmaCrossStrategy(Strategy):
    """Benchmark classique (exemple du README de backtesting.py) : croisement
    de deux moyennes mobiles simples, parametres fixes (pas d'optimisation
    sur donnees futures)."""

    n1 = 10
    n2 = 20

    def init(self):
        self.sma1 = self.I(_sma, self.data.Close, self.n1)
        self.sma2 = self.I(_sma, self.data.Close, self.n2)

    def next(self):
        if crossover(self.sma1, self.sma2):
            self.buy()
        elif crossover(self.sma2, self.sma1):
            self.position.close()


class BuyAndHoldStrategy(Strategy):
    """Benchmark le plus simple : achete a 100% des le premier jour
    disponible, ne revend jamais - reference incontournable pour juger si
    une strategie active (nos signaux ou SMA cross) apporte reellement
    quelque chose par rapport a ne rien faire."""

    def init(self):
        pass

    def next(self):
        if not self.position:
            self.buy()


_STRATEGY_CLASSES = {
    STRATEGY_SIGNAL_REPLAY: SignalReplayStrategy,
    STRATEGY_SMA_CROSS: SmaCrossStrategy,
    STRATEGY_BUY_AND_HOLD: BuyAndHoldStrategy,
}


async def run_kernc_backtest(
    db: AsyncSession,
    asset_id: uuid.UUID,
    strategy_name: str,
    period_start: date,
    period_end: date,
    horizon: str = "medium",
    cash: float = 10_000.0,
    commission: float = 0.001,
) -> dict | None:
    """
    Execute un backtest via backtesting.py pour un actif/strategie/periode
    donnes. Retourne un dict pret a passer a backtests/repository.py::save_result,
    ou None si les donnees sont insuffisantes (pas assez de cours, ou aucun
    signal stocke pour signal_replay) - traite comme "rien a rapporter" plutot
    que comme une erreur, coherent avec run_backtest_for_asset() (service.py)
    qui exclut deja les signaux sans prix futurs disponibles.
    """
    strategy_cls = _STRATEGY_CLASSES.get(strategy_name)
    if strategy_cls is None:
        raise ValueError(f"Strategie inconnue: {strategy_name}")

    df = await _load_price_dataframe(db, asset_id, period_start, period_end)
    if df.empty:
        return None

    run_kwargs = {}
    if strategy_name == STRATEGY_SIGNAL_REPLAY:
        signal_map = await _load_signal_map(db, asset_id, horizon, period_start, period_end)
        if not signal_map:
            return None
        run_kwargs["signal_map"] = signal_map

    # finalize_trades=True : une position encore ouverte a la fin de la
    # periode (frequent pour buy_and_hold, ou signal_replay si le dernier
    # signal connu est encore haussier) est cloturee fictivement au dernier
    # cours pour etre comptee dans "# Trades"/Win Rate/etc. - sans ca,
    # backtesting.py l'exclut silencieusement des stats, ce qui sous-estimerait
    # la performance reelle de la strategie.
    bt = Backtest(df, strategy_cls, cash=cash, commission=commission, exclusive_orders=True, finalize_trades=True)
    stats = bt.run(**run_kwargs)

    num_trades = _num(stats, "# Trades") or 0
    win_rate_pct = _num(stats, "Win Rate [%]")
    max_dd_pct = _num(stats, "Max. Drawdown [%]")

    return {
        # Champs types existants (memes unites que le moteur interne : ratios
        # 0-1, pas de %, drawdown en valeur absolue positive) pour permettre
        # une comparaison directe entre les deux moteurs.
        "precision": None,  # non applicable a une simulation cash (pas de notion de "succes de signal")
        "win_rate": (win_rate_pct / 100) if win_rate_pct is not None else None,
        "false_positive_rate": None,
        "max_drawdown": (abs(max_dd_pct) / 100) if max_dd_pct is not None else None,
        "signal_count": int(num_trades),
        "sharpe_ratio": _num(stats, "Sharpe Ratio"),
        "calmar_ratio": _num(stats, "Calmar Ratio"),
        "profit_factor": _num(stats, "Profit Factor"),
        "avg_risk_reward": None,  # pas d'equivalent direct dans les stats de backtesting.py
        "strategy_name": strategy_name,
        "extra_metrics": _stats_to_extra_metrics(stats),
    }
