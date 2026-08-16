"""
Strategies backtesting.py - miroir VOLONTAIRE des classes pures de
backend/app/domains/backtests/kernc_engine.py (14/08/2026).

Pourquoi une copie plutot qu'un import direct depuis `backend/app` : ce
dossier est un outil autonome qui tourne sur le PC de l'utilisateur, jamais
couple au NAS (voir README.md). Importer kernc_engine.py directement
entrainerait toute l'arborescence `app.*` a sa suite (settings Pydantic,
connexion DB, cle secrete JWT...) - une config qui n'existe pas et n'a pas
de raison d'exister sur un PC qui ne fait QUE lire des donnees publiques via
l'API et rejouer un backtest en memoire. Le cout de ce choix : ces classes
peuvent driver de l'original avec le temps si kernc_engine.py evolue - accepte
consciemment, a rementionner si un ecart de comportement est un jour
suspecte (comparer aux resultats affiches par /run-kernc dans l'app).

Ne couvre QUE les 5 strategies auto-suffisantes (prix seuls, aucune donnee
stockee cote application) : sma_cross, rsi_mean_reversion, macd_cross,
bollinger_reversion, buy_and_hold. `signal_replay` et le moteur interne
(`internal_rules`) sont volontairement HORS PERIMETRE de cet outil v1 : ils
dependent des scores de signaux deja stockes en base (table `signals`),
non exposes par l'API publique en lecture seule - les rejouer depuis ce PC
demanderait soit un acces direct a la base (rejete, voir README.md), soit
un nouvel endpoint cote NAS (rejete pour cette premiere version, voir
conversation du 14/08/2026 - "aucun risque, rien touche sur le NAS").
"""
import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover

STRATEGY_SMA_CROSS = "sma_cross"
STRATEGY_RSI = "rsi_mean_reversion"
STRATEGY_MACD = "macd_cross"
STRATEGY_BOLLINGER = "bollinger_reversion"
STRATEGY_BUY_AND_HOLD = "buy_and_hold"

SUPPORTED_STRATEGIES = (
    STRATEGY_SMA_CROSS,
    STRATEGY_RSI,
    STRATEGY_MACD,
    STRATEGY_BOLLINGER,
    STRATEGY_BUY_AND_HOLD,
)


def _sma(values, n):
    return pd.Series(values).rolling(n).mean()


def _ema_series(values, span):
    return pd.Series(values).ewm(span=span, adjust=False).mean()


def _rsi_series(values, period):
    s = pd.Series(values)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
    return rsi


def _macd_line(values, fast, slow):
    s = pd.Series(values)
    return s.ewm(span=fast, adjust=False).mean() - s.ewm(span=slow, adjust=False).mean()


def _bollinger_band(values, period, num_std, sign):
    s = pd.Series(values)
    sma = s.rolling(period).mean()
    std = s.rolling(period).std()
    return sma + sign * num_std * std


class SmaCrossStrategy(Strategy):
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


class RsiStrategy(Strategy):
    rsi_period = 14
    oversold = 30.0
    overbought = 70.0

    def init(self):
        self.rsi = self.I(_rsi_series, self.data.Close, self.rsi_period)

    def next(self):
        if crossover(self.rsi, self.oversold):
            self.buy()
        elif crossover(self.overbought, self.rsi):
            self.position.close()


class MacdStrategy(Strategy):
    fast = 12
    slow = 26
    signal = 9

    def init(self):
        self.macd = self.I(_macd_line, self.data.Close, self.fast, self.slow)
        self.macd_signal = self.I(_ema_series, self.macd, self.signal)

    def next(self):
        if crossover(self.macd, self.macd_signal):
            self.buy()
        elif crossover(self.macd_signal, self.macd):
            self.position.close()


class BollingerStrategy(Strategy):
    period = 20
    num_std = 2.0

    def init(self):
        close = self.data.Close
        self.upper = self.I(_bollinger_band, close, self.period, self.num_std, 1)
        self.lower = self.I(_bollinger_band, close, self.period, self.num_std, -1)

    def next(self):
        price = self.data.Close[-1]
        if price <= self.lower[-1] and not self.position:
            self.buy()
        elif price >= self.upper[-1] and self.position:
            self.position.close()


class BuyAndHoldStrategy(Strategy):
    def init(self):
        pass

    def next(self):
        if not self.position:
            self.buy()


STRATEGY_CLASSES = {
    STRATEGY_SMA_CROSS: SmaCrossStrategy,
    STRATEGY_RSI: RsiStrategy,
    STRATEGY_MACD: MacdStrategy,
    STRATEGY_BOLLINGER: BollingerStrategy,
    STRATEGY_BUY_AND_HOLD: BuyAndHoldStrategy,
}
