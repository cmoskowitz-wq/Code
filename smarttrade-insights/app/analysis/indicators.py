"""
SmartTrade Insights - Technical Indicators
All calculations are pure numpy/pandas – no external TA library needed.
"""
import numpy as np
import pandas as pd
from typing import Tuple, Optional


# ── Trend ─────────────────────────────────────────────────────────────────────

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average."""
    weights = np.arange(1, period + 1)

    def _wma(x):
        return np.dot(x, weights) / weights.sum()

    return series.rolling(window=period).apply(_wma, raw=True)


def vwap(df: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price (intraday reset via cumulative)."""
    tp = (df["high"] + df["low"] + df["close"]) / 3
    return (tp * df["volume"]).cumsum() / df["volume"].cumsum()


# ── Momentum ──────────────────────────────────────────────────────────────────

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder smoothing)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD indicator.
    Returns: (macd_line, signal_line, histogram)
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def momentum(series: pd.Series, period: int = 10) -> pd.Series:
    """Price Momentum = close / close[n] * 100 - 100."""
    return (series / series.shift(period) - 1) * 100


def rate_of_change(series: pd.Series, period: int = 10) -> pd.Series:
    """Rate of Change (%)."""
    return (series - series.shift(period)) / series.shift(period) * 100


def stochastic(
    df: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator.
    Returns (%K, %D)
    """
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min)
    d = sma(k, d_period)
    return k, d


# ── Volatility ────────────────────────────────────────────────────────────────

def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands.
    Returns: (upper, middle, lower)
    """
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    h_l = df["high"] - df["low"]
    h_pc = (df["high"] - df["close"].shift()).abs()
    l_pc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def historical_volatility(series: pd.Series, period: int = 20) -> pd.Series:
    """Annualised historical volatility (log returns)."""
    log_ret = np.log(series / series.shift(1))
    return log_ret.rolling(window=period).std() * np.sqrt(252) * 100


# ── Volume ────────────────────────────────────────────────────────────────────

def obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume."""
    direction = np.sign(df["close"].diff()).fillna(0)
    return (direction * df["volume"]).cumsum()


def volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Volume Simple Moving Average."""
    return sma(df["volume"].astype(float), period)


def relative_volume(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Relative Volume = current volume / average volume."""
    avg_vol = volume_sma(df, period)
    return df["volume"].astype(float) / avg_vol


# ── Composite indicator builder ───────────────────────────────────────────────

def compute_all(df: pd.DataFrame, config: Optional[dict] = None) -> pd.DataFrame:
    """
    Compute all indicators and attach them as new columns on a copy of df.
    config keys: rsi_period, sma_short, sma_medium, sma_long,
                 macd_fast, macd_slow, macd_signal,
                 bb_period, bb_std, atr_period, mom_period
    """
    cfg = config or {}
    rsi_p = cfg.get("rsi_period", 14)
    sma_s = cfg.get("sma_short", 20)
    sma_m = cfg.get("sma_medium", 50)
    sma_l = cfg.get("sma_long", 200)
    macd_f = cfg.get("macd_fast", 12)
    macd_sl = cfg.get("macd_slow", 26)
    macd_sig = cfg.get("macd_signal", 9)
    bb_p = cfg.get("bb_period", 20)
    bb_std = cfg.get("bb_std", 2.0)
    atr_p = cfg.get("atr_period", 14)
    mom_p = cfg.get("mom_period", 10)

    out = df.copy()
    close = out["close"]

    out["rsi"] = rsi(close, rsi_p)
    out["sma_short"] = sma(close, sma_s)
    out["sma_medium"] = sma(close, sma_m)
    out["sma_long"] = sma(close, sma_l)
    out["ema_fast"] = ema(close, macd_f)
    out["ema_slow"] = ema(close, macd_sl)
    out["macd"], out["macd_signal"], out["macd_hist"] = macd(close, macd_f, macd_sl, macd_sig)

    bb_upper, bb_mid, bb_lower = bollinger_bands(close, bb_p, bb_std)
    out["bb_upper"] = bb_upper
    out["bb_mid"] = bb_mid
    out["bb_lower"] = bb_lower
    out["bb_width"] = (bb_upper - bb_lower) / bb_mid * 100

    if "high" in out.columns and "low" in out.columns:
        out["atr"] = atr(out, atr_p)
        out["stoch_k"], out["stoch_d"] = stochastic(out)
        if "volume" in out.columns:
            out["obv"] = obv(out)
            out["rel_vol"] = relative_volume(out)

    out["momentum"] = momentum(close, mom_p)
    out["roc"] = rate_of_change(close, mom_p)
    out["hvol"] = historical_volatility(close)

    return out
