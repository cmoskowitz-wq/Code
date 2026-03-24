"""
analysis.py — Technical indicators and signal generation for TradeMe.
"""
from __future__ import annotations

import pandas as pd


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute MA20, MA50, RSI, MACD, and Bollinger Bands in-place copy."""
    df = df.copy()

    # Moving averages
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    # RSI — Wilder smoothing (EMA with com=13)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD (12/26/9)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # Bollinger Bands (20-period, ±2σ)
    std = df["Close"].rolling(20).std()
    df["BB_upper"] = df["MA20"] + 2 * std
    df["BB_lower"] = df["MA20"] - 2 * std

    return df


def generate_signal(df: pd.DataFrame) -> tuple[str, int, list[str]]:
    """
    Analyse the most recent bar and return:
        (signal_label, confidence_pct, [reason_strings])

    Signal labels: STRONG BUY | BUY | HOLD | SELL | STRONG SELL
    """
    latest = df.iloc[-1]
    score = 0
    reasons: list[str] = []

    # ── RSI ───────────────────────────────────────────────────────────────────
    rsi = latest.get("RSI", float("nan"))
    if pd.notna(rsi):
        if rsi < 30:
            score += 2
            reasons.append(f"RSI {rsi:.1f} — oversold (bullish)")
        elif rsi < 45:
            score += 1
            reasons.append(f"RSI {rsi:.1f} — approaching oversold")
        elif rsi > 70:
            score -= 2
            reasons.append(f"RSI {rsi:.1f} — overbought (bearish)")
        elif rsi > 55:
            score -= 1
            reasons.append(f"RSI {rsi:.1f} — approaching overbought")
        else:
            reasons.append(f"RSI {rsi:.1f} — neutral")

    # ── Moving average trend ──────────────────────────────────────────────────
    ma20 = latest.get("MA20", float("nan"))
    ma50 = latest.get("MA50", float("nan"))
    if pd.notna(ma20) and pd.notna(ma50):
        if ma20 > ma50:
            score += 1
            reasons.append("MA20 > MA50 — uptrend confirmed")
        else:
            score -= 1
            reasons.append("MA20 < MA50 — downtrend")

    # ── Price vs MA20 ─────────────────────────────────────────────────────────
    close = latest["Close"]
    if pd.notna(ma20) and ma20 > 0:
        deviation = (close / ma20 - 1) * 100
        if deviation > 2:
            score += 1
            reasons.append(f"Price +{deviation:.1f}% above MA20 — momentum")
        elif deviation < -2:
            score -= 1
            reasons.append(f"Price {deviation:.1f}% below MA20 — weakness")

    # ── MACD ─────────────────────────────────────────────────────────────────
    macd = latest.get("MACD", float("nan"))
    macd_sig = latest.get("MACD_signal", float("nan"))
    if pd.notna(macd) and pd.notna(macd_sig):
        if macd > macd_sig:
            score += 1
            reasons.append("MACD above signal line — bullish momentum")
        else:
            score -= 1
            reasons.append("MACD below signal line — bearish momentum")

    # ── 5-day price momentum ──────────────────────────────────────────────────
    if len(df) >= 5:
        momentum = (df["Close"].iloc[-1] - df["Close"].iloc[-5]) / df["Close"].iloc[-5] * 100
        if momentum > 2:
            score += 1
            reasons.append(f"5-day momentum +{momentum:.1f}% — positive")
        elif momentum < -2:
            score -= 1
            reasons.append(f"5-day momentum {momentum:.1f}% — negative")
        else:
            reasons.append(f"5-day momentum {momentum:+.1f}% — flat")

    # ── Bollinger Band extremes ───────────────────────────────────────────────
    bb_upper = latest.get("BB_upper", float("nan"))
    bb_lower = latest.get("BB_lower", float("nan"))
    if pd.notna(bb_upper) and pd.notna(bb_lower):
        if close > bb_upper:
            score -= 1
            reasons.append("Price above upper Bollinger Band — extended")
        elif close < bb_lower:
            score += 1
            reasons.append("Price below lower Bollinger Band — potential reversal")

    # ── Map score → label ─────────────────────────────────────────────────────
    if score >= 4:
        signal = "STRONG BUY"
    elif score >= 2:
        signal = "BUY"
    elif score <= -4:
        signal = "STRONG SELL"
    elif score <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    max_score = 8
    confidence = int(min(100, max(30, 50 + (score / max_score) * 50)))
    return signal, confidence, reasons
