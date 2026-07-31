"""
Bac a sable pedagogique (31/07/2026) - voir docs/STACK.md pour la discussion
complete et la decision d'isolation. CE MODULE N'EST JAMAIS UTILISE PAR LE
MOTEUR DE SIGNAL REEL (signals/models_ml/baseline_rules.py) NI PAR LE
PORTEFEUILLE VIRTUEL - il sert exclusivement a explorer/apprendre l'analyse
technique classique, en comparaison du moteur de regles explicable qui reste
seul a produire de "vrais" signaux (voir analysis_lab/service.py pour la
comparaison cote a cote).

Inspire par le framework externe fourni par l'utilisateur (feature_engineering.py
de son "trading_prediction_framework", voir DOCUMENTATION.md) - reimplemente
ici en pandas pur (pas de TA-Lib, qui demande une compilation C souvent
penible a installer) pour rester coherent avec le style deja utilise dans
market_data/service.py (SMA/EMA/RSI/MACD/Bollinger deja recalcules a la main).

Toutes les fonctions sont PURES (DataFrame en entree, DataFrame/Series en
sortie, aucun acces DB/reseau) - testables independamment (voir
tests/test_analysis_lab_features.py).

Convention d'entree : un DataFrame indexe par date (croissant), colonnes
Open/High/Low/Close/Volume (memes noms que kernc_engine.py, pour pouvoir
reutiliser directement un DataFrame deja construit ailleurs dans le projet).
"""
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Tendance (Trend)
# ---------------------------------------------------------------------------

SMA_PERIODS = (5, 10, 20, 50, 100, 200)
EMA_PERIODS = (5, 10, 20, 50, 100, 200)


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for n in SMA_PERIODS:
        df[f"sma_{n}"] = df["Close"].rolling(n).mean()
    for n in EMA_PERIODS:
        df[f"ema_{n}"] = df["Close"].ewm(span=n, adjust=False).mean()
    return df


def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema_12 - ema_26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["Close"].shift(1)
    ranges = pd.concat(
        [df["High"] - df["Low"], (df["High"] - prev_close).abs(), (df["Low"] - prev_close).abs()], axis=1
    )
    return ranges.max(axis=1)


def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Average Directional Index (Wilder, 1978) - mesure la FORCE d'une tendance
    (pas sa direction : un ADX eleve peut accompagner une tendance haussiere
    OU baissiere). +DI/-DI (inclus aussi) donnent la direction.
    """
    df = df.copy()
    up_move = df["High"].diff()
    down_move = -df["Low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = _true_range(df)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()

    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / period, adjust=False).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df["plus_di_14"] = plus_di
    df["minus_di_14"] = minus_di
    df["adx_14"] = dx.ewm(alpha=1 / period, adjust=False).mean()
    return df


def add_aroon(df: pd.DataFrame, period: int = 25) -> pd.DataFrame:
    """
    Aroon Oscillator = Aroon Up - Aroon Down, entre -100 et +100.
    Aroon Up = 100 * (period - jours depuis le plus haut) / period, idem pour
    Aroon Down avec le plus bas - mesure la RECENCE des extremes, pas leur
    ampleur (complementaire du RSI/momentum classique).
    """
    df = df.copy()
    rolling_high_idx = df["High"].rolling(period + 1).apply(lambda x: period - np.argmax(x[::-1]), raw=True)
    rolling_low_idx = df["Low"].rolling(period + 1).apply(lambda x: period - np.argmin(x[::-1]), raw=True)
    aroon_up = 100 * (period - rolling_high_idx) / period
    aroon_down = 100 * (period - rolling_low_idx) / period
    df["aroon_oscillator"] = aroon_up - aroon_down
    return df


def add_parabolic_sar(df: pd.DataFrame, af_step: float = 0.02, af_max: float = 0.2) -> pd.DataFrame:
    """
    Parabolic SAR (Wilder) - point d'inversion de tendance suggere, calcule de
    facon ITERATIVE (pas vectorisable comme les autres indicateurs) : chaque
    valeur depend de la precedente et d'un facteur d'acceleration qui
    s'incremente a chaque nouvel extreme. Boucle Python assumee (couteuse sur
    un tres long historique, acceptable ici - quelques centaines de barres).
    """
    df = df.copy()
    high, low, close = df["High"].values, df["Low"].values, df["Close"].values
    n = len(df)
    sar = np.full(n, np.nan)
    if n < 2:
        df["parabolic_sar"] = sar
        return df

    uptrend = close[1] >= close[0]
    af = af_step
    ep = high[0] if uptrend else low[0]
    sar[0] = low[0] if uptrend else high[0]

    for i in range(1, n):
        prev_sar = sar[i - 1]
        sar[i] = prev_sar + af * (ep - prev_sar)
        if uptrend:
            sar[i] = min(sar[i], low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
            if high[i] > ep:
                ep = high[i]
                af = min(af + af_step, af_max)
            if low[i] < sar[i]:
                uptrend = False
                sar[i] = ep
                ep = low[i]
                af = af_step
        else:
            sar[i] = max(sar[i], high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
            if low[i] < ep:
                ep = low[i]
                af = min(af + af_step, af_max)
            if high[i] > sar[i]:
                uptrend = True
                sar[i] = ep
                ep = high[i]
                af = af_step

    df["parabolic_sar"] = sar
    return df


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------

RSI_PERIODS = (7, 14, 21)


def _rsi(closes: pd.Series, period: int) -> pd.Series:
    """Meme formule que market_data/service.py::_rsi (Wilder) - dupliquee
    volontairement ici plutot qu'importee, pour garder ce domaine isole
    (voir docstring de module)."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
    return rsi


def add_rsi_multi(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for n in RSI_PERIODS:
        df[f"rsi_{n}"] = _rsi(df["Close"], n)
    return df


def add_stochastic(df: pd.DataFrame, period: int = 14, smooth_d: int = 3) -> pd.DataFrame:
    df = df.copy()
    lowest_low = df["Low"].rolling(period).min()
    highest_high = df["High"].rolling(period).max()
    percent_k = 100 * (df["Close"] - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    df["stochastic_k"] = percent_k
    df["stochastic_d"] = percent_k.rolling(smooth_d).mean()
    return df


def add_cci(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Commodity Channel Index - ecart du prix typique a sa moyenne mobile,
    normalise par l'ecart absolu moyen (constante 0.015 = convention Lambert
    d'origine, calibree pour que ~70-80% des valeurs restent dans [-100, 100])."""
    df = df.copy()
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    sma_tp = typical_price.rolling(period).mean()
    mean_deviation = typical_price.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    df["cci_20"] = (typical_price - sma_tp) / (0.015 * mean_deviation.replace(0, np.nan))
    return df


def add_williams_r(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df = df.copy()
    highest_high = df["High"].rolling(period).max()
    lowest_low = df["Low"].rolling(period).min()
    df["williams_r_14"] = -100 * (highest_high - df["Close"]) / (highest_high - lowest_low).replace(0, np.nan)
    return df


def add_roc(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    df = df.copy()
    df[f"roc_{period}"] = df["Close"].pct_change(periods=period) * 100
    return df


def add_mfi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Money Flow Index - "RSI pondere par le volume". Necessite Volume,
    contrairement au RSI classique."""
    df = df.copy()
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    raw_money_flow = typical_price * df["Volume"]
    price_up = typical_price.diff() > 0
    positive_flow = raw_money_flow.where(price_up, 0.0).rolling(period).sum()
    negative_flow = raw_money_flow.where(~price_up, 0.0).rolling(period).sum()
    money_ratio = positive_flow / negative_flow.replace(0, np.nan)
    df["mfi_14"] = 100 - (100 / (1 + money_ratio))
    return df


# ---------------------------------------------------------------------------
# Volatilite
# ---------------------------------------------------------------------------


def add_bollinger(df: pd.DataFrame, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    df = df.copy()
    sma = df["Close"].rolling(period).mean()
    std = df["Close"].rolling(period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    df["bollinger_upper"] = upper
    df["bollinger_lower"] = lower
    df["bollinger_width"] = (upper - lower) / sma.replace(0, np.nan)
    df["bollinger_position"] = (df["Close"] - lower) / (upper - lower).replace(0, np.nan)
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df = df.copy()
    df[f"atr_{period}"] = _true_range(df).ewm(alpha=1 / period, adjust=False).mean()
    return df


def add_keltner_channels(df: pd.DataFrame, period: int = 20, atr_period: int = 10, multiplier: float = 2.0) -> pd.DataFrame:
    df = df.copy()
    middle = df["Close"].ewm(span=period, adjust=False).mean()
    atr = _true_range(df).ewm(alpha=1 / atr_period, adjust=False).mean()
    df["keltner_middle"] = middle
    df["keltner_upper"] = middle + multiplier * atr
    df["keltner_lower"] = middle - multiplier * atr
    return df


def add_historical_volatility(df: pd.DataFrame, period: int = 20, trading_days_per_year: int = 252) -> pd.DataFrame:
    """
    Volatilite historique ANNUALISEE (convention standard du secteur), a
    partir des rendements LOGARITHMIQUES - distincte de `volatility_20d` deja
    calcule dans market_data/service.py (ecart-type simple des rendements en
    %, non annualise) : les deux coexistent volontairement, l'une pour le
    moteur de signal (simplicite), l'autre ici pour la convention "manuel de
    finance" (comparaison directe avec un Sharpe/une vol annualisee affichee
    ailleurs, ex. backtests/kernc_engine.py)."""
    df = df.copy()
    log_returns = np.log(df["Close"] / df["Close"].shift(1))
    df[f"historical_volatility_{period}"] = log_returns.rolling(period).std() * np.sqrt(trading_days_per_year)
    return df


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------


def add_obv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    direction = np.sign(df["Close"].diff().fillna(0))
    df["obv"] = (direction * df["Volume"]).cumsum()
    return df


def add_cmf(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Chaikin Money Flow - pression acheteuse/vendeuse ponderee par le
    volume, bornee approximativement entre -1 et +1."""
    df = df.copy()
    money_flow_multiplier = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / (df["High"] - df["Low"]).replace(
        0, np.nan
    )
    money_flow_volume = money_flow_multiplier * df["Volume"]
    df["cmf_20"] = money_flow_volume.rolling(period).sum() / df["Volume"].rolling(period).sum().replace(0, np.nan)
    return df


def add_vwap(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    VWAP GLISSANT sur `period` barres - approximation assumee : le VWAP
    "classique" se calcule intra-journalier (a partir de donnees tick/minute
    et se remet a zero chaque session), inapplicable ici car on ne dispose
    que de barres QUOTIDIENNES (voir price_bars). Cette version glissante sur
    plusieurs jours est une convention differente, courante en analyse
    multi-jours, mais a ne pas confondre avec le VWAP intraday d'un trader actif.
    """
    df = df.copy()
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    df[f"vwap_{period}"] = (typical_price * df["Volume"]).rolling(period).sum() / df["Volume"].rolling(
        period
    ).sum().replace(0, np.nan)
    return df


def add_force_index(df: pd.DataFrame, smoothing: int = 13) -> pd.DataFrame:
    df = df.copy()
    raw_force = df["Close"].diff() * df["Volume"]
    df["force_index_13"] = raw_force.ewm(span=smoothing, adjust=False).mean()
    return df


# ---------------------------------------------------------------------------
# Features temporelles
# ---------------------------------------------------------------------------


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    idx = df.index
    df["day_of_week"] = idx.dayofweek
    df["month"] = idx.month
    df["quarter"] = idx.quarter
    df["is_month_start"] = idx.is_month_start.astype(int)
    df["is_month_end"] = idx.is_month_end.astype(int)
    df["is_quarter_start"] = idx.is_quarter_start.astype(int)
    df["is_quarter_end"] = idx.is_quarter_end.astype(int)
    # Encodage cyclique : evite qu'un modele interprete "vendredi" (4) et
    # "lundi" (0) comme "loin l'un de l'autre" alors qu'ils sont adjacents
    # dans le cycle hebdomadaire - meme logique pour le mois (decembre/janvier).
    df["day_of_week_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["day_of_week_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    return df


# ---------------------------------------------------------------------------
# Features derivees
# ---------------------------------------------------------------------------

LAG_PERIODS = (1, 2, 3, 5, 10, 20)
ROLLING_STATS_WINDOW = 20


def add_lags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for n in LAG_PERIODS:
        df[f"close_lag_{n}"] = df["Close"].shift(n)
    return df


def add_rolling_stats(df: pd.DataFrame, window: int = ROLLING_STATS_WINDOW) -> pd.DataFrame:
    df = df.copy()
    returns = df["Close"].pct_change()
    rolling = returns.rolling(window)
    df[f"returns_mean_{window}"] = rolling.mean()
    df[f"returns_std_{window}"] = rolling.std()
    df[f"returns_min_{window}"] = rolling.min()
    df[f"returns_max_{window}"] = rolling.max()
    df[f"returns_skew_{window}"] = rolling.skew()
    df[f"returns_kurt_{window}"] = rolling.kurt()
    return df


def add_relative_price_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["price_range"] = df["High"] - df["Low"]
    df["price_position"] = (df["Close"] - df["Low"]) / (df["High"] - df["Low"]).replace(0, np.nan)
    df["price_gap"] = df["Open"] - df["Close"].shift(1)
    return df


def add_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sous-ensemble pedagogique de patterns de chandeliers (pas une
    bibliotheque exhaustive type TA-Lib) - regles simples et lisibles,
    volontairement approximatives (les vraies definitions varient d'un auteur
    a l'autre) : sert a illustrer le concept, pas a etre une reference
    professionnelle de reconnaissance de patterns.
    """
    df = df.copy()
    body = (df["Close"] - df["Open"]).abs()
    candle_range = (df["High"] - df["Low"]).replace(0, np.nan)
    prev_open = df["Open"].shift(1)
    prev_close = df["Close"].shift(1)

    df["is_doji"] = (body / candle_range < 0.1).astype(int)
    df["is_bullish_engulfing"] = (
        (df["Close"] > df["Open"]) & (prev_close < prev_open) & (df["Close"] > prev_open) & (df["Open"] < prev_close)
    ).astype(int)
    df["is_bearish_engulfing"] = (
        (df["Close"] < df["Open"]) & (prev_close > prev_open) & (df["Close"] < prev_open) & (df["Open"] > prev_close)
    ).astype(int)
    lower_shadow = df[["Open", "Close"]].min(axis=1) - df["Low"]
    upper_shadow = df["High"] - df[["Open", "Close"]].max(axis=1)
    df["is_hammer"] = ((lower_shadow > 2 * body) & (upper_shadow < body)).astype(int)
    return df


def generate_all_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Orchestrateur unique : applique toutes les fonctions ci-dessus dans
    l'ordre et retourne un DataFrame enrichi (colonnes d'origine OHLCV +
    50+ colonnes de features). Fonction pure, aucun acces DB.
    """
    result = df.copy()
    for step in (
        add_moving_averages,
        add_macd,
        add_adx,
        add_aroon,
        add_parabolic_sar,
        add_rsi_multi,
        add_stochastic,
        add_cci,
        add_williams_r,
        add_roc,
        add_mfi,
        add_bollinger,
        add_atr,
        add_keltner_channels,
        add_historical_volatility,
        add_obv,
        add_cmf,
        add_vwap,
        add_force_index,
        add_temporal_features,
        add_lags,
        add_rolling_stats,
        add_relative_price_features,
        add_candlestick_patterns,
    ):
        result = step(result)
    return result


class FeatureEngineer:
    """
    Enveloppe fine autour de generate_all_features(), pour une API proche de
    celle decrite par l'utilisateur (DOCUMENTATION.md : `engineer =
    FeatureEngineer(); df = engineer.generate_all_features(df)`). Purement
    cosmetique - toute la logique reste dans les fonctions pures ci-dessus.
    """

    def __init__(self):
        self.feature_names: list[str] = []

    def generate_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        result = generate_all_features(df)
        original_columns = set(df.columns)
        self.feature_names = [c for c in result.columns if c not in original_columns]
        return result
