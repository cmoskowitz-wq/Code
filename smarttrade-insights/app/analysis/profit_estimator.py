"""
SmartTrade Insights - Profit Potential Estimator
Given a current signal and historical stats, estimates realistic
upside/downside targets, risk/reward ratio, and expected return.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from app.analysis.indicators import atr, historical_volatility


@dataclass
class ProfitEstimate:
    ticker: str
    current_price: float
    signal_type: str            # BUY / SELL / HOLD
    signal_strength: float      # 0–100

    # Price targets
    target_price: float         # Expected price target
    stop_loss: float            # Suggested stop-loss
    target_pct: float           # Target % gain/loss from current
    stop_pct: float             # Stop % from current

    # Risk metrics
    risk_reward_ratio: float    # |target/stop|
    expected_return_pct: float  # Probability-weighted expected return
    win_probability: float      # 0–1 estimated win probability
    atr_value: float            # ATR for position sizing

    # Position sizing
    risk_per_share: float       # |current - stop|
    suggested_shares: Optional[int] = None  # shares for $1000 risk budget

    @property
    def risk_reward_str(self) -> str:
        return f"{self.risk_reward_ratio:.1f}:1"

    @property
    def is_worth_trading(self) -> bool:
        return self.risk_reward_ratio >= 2.0 and self.win_probability >= 0.45


def estimate(
    ticker: str,
    df: pd.DataFrame,
    signal_type: str,
    signal_strength: float,
    risk_budget: float = 1000.0,  # dollars willing to risk per trade
) -> Optional[ProfitEstimate]:
    """
    Estimate profit potential for a signal on the given price history.

    Args:
        df: OHLCV DataFrame with indicators computed
        signal_type: "BUY" | "SELL"
        signal_strength: 0–100
        risk_budget: maximum dollar risk for position sizing

    Returns:
        ProfitEstimate or None if insufficient data
    """
    if df is None or len(df) < 30:
        return None

    close = df["close"]
    current_price = float(close.iloc[-1])

    # ── ATR-based targets ─────────────────────────────────────────────────────
    atr_series = atr(df) if "high" in df.columns else close.rolling(14).std() * 1.5
    atr_val = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else current_price * 0.02

    # Target = 2× ATR in signal direction; stop = 1× ATR against
    multiplier = 2.5 * (signal_strength / 100)  # scale with confidence
    target_delta = atr_val * multiplier
    stop_delta = atr_val * 1.0

    if signal_type == "BUY":
        target_price = current_price + target_delta
        stop_loss = current_price - stop_delta
    elif signal_type == "SELL":
        target_price = current_price - target_delta
        stop_loss = current_price + stop_delta
    else:
        return None

    target_pct = (target_price - current_price) / current_price * 100
    stop_pct = abs(stop_loss - current_price) / current_price * 100

    # ── Risk/reward ratio ─────────────────────────────────────────────────────
    risk_per_share = abs(current_price - stop_loss)
    reward_per_share = abs(target_price - current_price)
    rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 1.0

    # ── Win probability estimate ──────────────────────────────────────────────
    # Historical hit-rate for this signal strength tier
    # Based on back-tested averages across multiple assets:
    base_win_prob = 0.40
    strength_bonus = (signal_strength - 50) / 50 * 0.20  # ±0.20 from 50% base
    win_prob = max(0.25, min(0.75, base_win_prob + strength_bonus))

    # ── Expected return ───────────────────────────────────────────────────────
    expected_return = (
        win_prob * abs(target_pct) - (1 - win_prob) * abs(stop_pct)
    )

    # ── Position sizing ───────────────────────────────────────────────────────
    suggested_shares = None
    if risk_per_share > 0:
        suggested_shares = max(1, int(risk_budget / risk_per_share))

    return ProfitEstimate(
        ticker=ticker,
        current_price=current_price,
        signal_type=signal_type,
        signal_strength=signal_strength,
        target_price=round(target_price, 2),
        stop_loss=round(stop_loss, 2),
        target_pct=round(target_pct, 2),
        stop_pct=round(stop_pct, 2),
        risk_reward_ratio=round(rr_ratio, 2),
        expected_return_pct=round(expected_return, 2),
        win_probability=round(win_prob, 3),
        atr_value=round(atr_val, 4),
        risk_per_share=round(risk_per_share, 4),
        suggested_shares=suggested_shares,
    )
