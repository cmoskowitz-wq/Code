"""
SmartTrade Insights - Signal Generation Engine
Combines multiple indicator signals into a composite score and
generates BUY / SELL / HOLD recommendations with strength 0–100.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.analysis.indicators import compute_all
from app.config import (
    RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    SMA_SHORT, SMA_MEDIUM, SMA_LONG,
    EMA_FAST, EMA_SLOW, MACD_SIGNAL,
    WEIGHT_RSI, WEIGHT_MA_CROSS, WEIGHT_MOMENTUM, WEIGHT_VOLUME,
    STRONG_SIGNAL_THRESHOLD, MODERATE_SIGNAL_THRESHOLD,
)

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    ticker: str
    signal_type: str        # "BUY" | "SELL" | "HOLD"
    strength: float         # 0–100
    timestamp: str
    price: float
    rsi: Optional[float] = None
    sma_short: Optional[float] = None
    sma_medium: Optional[float] = None
    sma_long: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    momentum: Optional[float] = None
    notes: List[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        if self.strength >= STRONG_SIGNAL_THRESHOLD:
            return f"Strong {self.signal_type}"
        if self.strength >= MODERATE_SIGNAL_THRESHOLD:
            return f"Moderate {self.signal_type}"
        return self.signal_type

    def to_db_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "timestamp": self.timestamp,
            "signal_type": self.signal_type,
            "strength": self.strength,
            "rsi": self.rsi,
            "sma_short": self.sma_short,
            "sma_medium": self.sma_medium,
            "sma_long": self.sma_long,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "momentum": self.momentum,
            "notes": " | ".join(self.notes),
        }


class SignalEngine:
    """Generates composite buy/sell/hold signals from indicator data."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    # ── Public API ────────────────────────────────────────────────────────────

    def analyse(self, ticker: str, df: pd.DataFrame) -> Optional[Signal]:
        """
        Run full analysis on a price DataFrame and return the latest signal.
        df must have at least a 'close' column.
        """
        if df is None or len(df) < max(SMA_MEDIUM, 30):
            logger.debug("Insufficient data for %s (%d rows)", ticker, len(df) if df is not None else 0)
            return None

        try:
            idf = compute_all(df, self.config)
            return self._generate_signal(ticker, idf)
        except Exception as e:
            logger.error("SignalEngine.analyse(%s) error: %s", ticker, e)
            return None

    def analyse_row(self, ticker: str, idf: pd.DataFrame) -> Optional[Signal]:
        """Generate signal from pre-computed indicator DataFrame."""
        return self._generate_signal(ticker, idf)

    # ── Signal generation ─────────────────────────────────────────────────────

    def _generate_signal(self, ticker: str, idf: pd.DataFrame) -> Optional[Signal]:
        row = idf.iloc[-1]
        price = float(row["close"])
        notes: List[str] = []

        rsi_score, rsi_direction = self._score_rsi(row, notes)
        ma_score, ma_direction = self._score_ma(row, idf, notes)
        mom_score, mom_direction = self._score_momentum(row, notes)
        vol_score, vol_direction = self._score_volume(row, idf, notes)

        # Weighted composite score (–100 to +100)
        composite = (
            rsi_score * WEIGHT_RSI
            + ma_score * WEIGHT_MA_CROSS
            + mom_score * WEIGHT_MOMENTUM
            + vol_score * WEIGHT_VOLUME
        )

        # Translate composite to BUY/SELL/HOLD + strength
        if composite > 20:
            signal_type = "BUY"
            strength = min(100.0, 50 + composite)
        elif composite < -20:
            signal_type = "SELL"
            strength = min(100.0, 50 + abs(composite))
        else:
            signal_type = "HOLD"
            strength = 50.0

        return Signal(
            ticker=ticker,
            signal_type=signal_type,
            strength=round(strength, 1),
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            price=price,
            rsi=_safe(row, "rsi"),
            sma_short=_safe(row, "sma_short"),
            sma_medium=_safe(row, "sma_medium"),
            sma_long=_safe(row, "sma_long"),
            macd=_safe(row, "macd"),
            macd_signal=_safe(row, "macd_signal"),
            momentum=_safe(row, "momentum"),
            notes=notes,
        )

    # ── Component scorers (return –100 to +100) ───────────────────────────────

    def _score_rsi(self, row: pd.Series, notes: List[str]) -> Tuple[float, str]:
        rsi_val = _safe(row, "rsi")
        if rsi_val is None:
            return 0.0, "HOLD"

        rsi_ob = self.config.get("rsi_overbought", RSI_OVERBOUGHT)
        rsi_os = self.config.get("rsi_oversold", RSI_OVERSOLD)

        if rsi_val <= rsi_os:
            score = 100.0
            direction = "BUY"
            notes.append(f"RSI oversold ({rsi_val:.1f})")
        elif rsi_val <= rsi_os + 10:
            score = 60.0
            direction = "BUY"
            notes.append(f"RSI approaching oversold ({rsi_val:.1f})")
        elif rsi_val >= rsi_ob:
            score = -100.0
            direction = "SELL"
            notes.append(f"RSI overbought ({rsi_val:.1f})")
        elif rsi_val >= rsi_ob - 10:
            score = -60.0
            direction = "SELL"
            notes.append(f"RSI approaching overbought ({rsi_val:.1f})")
        else:
            # Linearly interpolate in the neutral zone
            midpoint = (rsi_ob + rsi_os) / 2
            score = (midpoint - rsi_val) / (midpoint - rsi_os) * 30
            direction = "BUY" if score > 0 else "SELL"
        return score, direction

    def _score_ma(
        self, row: pd.Series, idf: pd.DataFrame, notes: List[str]
    ) -> Tuple[float, str]:
        score = 0.0
        close = float(row["close"])

        sma_s = _safe(row, "sma_short")
        sma_m = _safe(row, "sma_medium")
        sma_l = _safe(row, "sma_long")

        if sma_s and sma_m:
            if close > sma_s > sma_m:
                score += 40
                notes.append("Price above short+medium MA (bullish)")
            elif close < sma_s < sma_m:
                score -= 40
                notes.append("Price below short+medium MA (bearish)")

        if sma_l and close:
            if close > sma_l:
                score += 20
                notes.append("Price above 200 SMA")
            else:
                score -= 20
                notes.append("Price below 200 SMA")

        # Golden / Death cross detection (last 5 bars)
        if len(idf) >= 5 and sma_s and sma_m:
            prev_sma_s = _safe(idf.iloc[-5], "sma_short")
            prev_sma_m = _safe(idf.iloc[-5], "sma_medium")
            if prev_sma_s and prev_sma_m:
                cross_now = sma_s - sma_m
                cross_prev = prev_sma_s - prev_sma_m
                if cross_prev <= 0 < cross_now:
                    score += 40
                    notes.append("Golden cross (SMA20 crossed above SMA50)")
                elif cross_prev >= 0 > cross_now:
                    score -= 40
                    notes.append("Death cross (SMA20 crossed below SMA50)")

        # MACD cross
        macd_v = _safe(row, "macd")
        macd_sig = _safe(row, "macd_signal")
        if macd_v is not None and macd_sig is not None:
            if macd_v > macd_sig:
                score += 20
                notes.append("MACD above signal line")
            elif macd_v < macd_sig:
                score -= 20
                notes.append("MACD below signal line")

        return max(-100.0, min(100.0, score)), "BUY" if score > 0 else "SELL"

    def _score_momentum(self, row: pd.Series, notes: List[str]) -> Tuple[float, str]:
        mom = _safe(row, "momentum")
        roc = _safe(row, "roc")
        if mom is None and roc is None:
            return 0.0, "HOLD"

        score = 0.0
        val = mom if mom is not None else roc
        if val > 5:
            score = min(100.0, val * 5)
            notes.append(f"Positive momentum ({val:.1f}%)")
        elif val < -5:
            score = max(-100.0, val * 5)
            notes.append(f"Negative momentum ({val:.1f}%)")
        return score, "BUY" if score > 0 else "SELL"

    def _score_volume(
        self, row: pd.Series, idf: pd.DataFrame, notes: List[str]
    ) -> Tuple[float, str]:
        rel_vol = _safe(row, "rel_vol")
        if rel_vol is None:
            return 0.0, "HOLD"

        close = float(row["close"])
        prev_close = float(idf.iloc[-2]["close"]) if len(idf) >= 2 else close

        price_up = close > prev_close
        if rel_vol > 1.5:
            score = 60.0 if price_up else -60.0
            direction = "BUY" if price_up else "SELL"
            notes.append(
                f"High relative volume ({rel_vol:.1f}x) on {'up' if price_up else 'down'} move"
            )
        elif rel_vol > 1.2:
            score = 30.0 if price_up else -30.0
            direction = "BUY" if price_up else "SELL"
        else:
            score = 0.0
            direction = "HOLD"
        return score, direction

    # ── Batch analysis ────────────────────────────────────────────────────────

    def analyse_batch(
        self, tickers_dfs: Dict[str, pd.DataFrame]
    ) -> Dict[str, Optional[Signal]]:
        return {
            ticker: self.analyse(ticker, df)
            for ticker, df in tickers_dfs.items()
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(row: pd.Series, col: str) -> Optional[float]:
    val = row.get(col)
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return round(float(val), 6)
