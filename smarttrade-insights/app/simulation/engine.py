"""
SmartTrade Insights - Historical Simulation / Backtesting Engine
Runs a configurable buy/sell strategy over historical price data
and returns a detailed performance report.
"""
import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.analysis.indicators import compute_all
from app.analysis.signals import SignalEngine

logger = logging.getLogger(__name__)


# ── Strategy parameters ───────────────────────────────────────────────────────

@dataclass
class StrategyParams:
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    sma_short: int = 20
    sma_medium: int = 50
    sma_long: int = 200
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    min_signal_strength: float = 55.0  # only trade signals above this threshold
    stop_loss_pct: float = 5.0         # % stop loss
    take_profit_pct: float = 10.0      # % take profit (0 = signal-based exit)
    position_size_pct: float = 100.0   # % of available cash per trade

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, s: str) -> "StrategyParams":
        return cls(**json.loads(s))


# ── Trade record ──────────────────────────────────────────────────────────────

@dataclass
class TradeRecord:
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    shares: float
    pnl: float
    pnl_pct: float
    trade_type: str = "LONG"
    exit_reason: str = ""   # "signal" | "stop_loss" | "take_profit" | "end_of_data"


# ── Simulation result ─────────────────────────────────────────────────────────

@dataclass
class SimulationResult:
    ticker: str
    start_date: str
    end_date: str
    initial_invest: float
    final_value: float
    total_return_pct: float
    max_drawdown_pct: float
    win_rate_pct: float
    total_trades: int
    sharpe_ratio: float
    trades: List[TradeRecord] = field(default_factory=list)
    equity_curve: List[Dict] = field(default_factory=list)
    strategy_params: Optional[StrategyParams] = None

    @property
    def profitable(self) -> bool:
        return self.total_return_pct > 0

    @property
    def avg_trade_pnl_pct(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.pnl_pct for t in self.trades) / len(self.trades)

    @property
    def best_trade(self) -> Optional[TradeRecord]:
        return max(self.trades, key=lambda t: t.pnl_pct) if self.trades else None

    @property
    def worst_trade(self) -> Optional[TradeRecord]:
        return min(self.trades, key=lambda t: t.pnl_pct) if self.trades else None

    def to_db_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_invest": self.initial_invest,
            "final_value": self.final_value,
            "total_return_pct": self.total_return_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "win_rate_pct": self.win_rate_pct,
            "total_trades": self.total_trades,
            "sharpe_ratio": self.sharpe_ratio,
            "strategy_params": self.strategy_params.to_json() if self.strategy_params else "{}",
        }

    def trades_to_db_list(self) -> List[Dict]:
        return [
            {
                "entry_date": t.entry_date,
                "exit_date": t.exit_date,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "shares": t.shares,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "trade_type": t.trade_type,
            }
            for t in self.trades
        ]


# ── Engine ────────────────────────────────────────────────────────────────────

class SimulationEngine:
    """
    Event-driven backtester.
    Processes each bar in order, applying the signal strategy.
    """

    def __init__(self, params: Optional[StrategyParams] = None):
        self.params = params or StrategyParams()
        self._signal_engine = SignalEngine(
            config={
                "rsi_period": self.params.rsi_period,
                "rsi_overbought": self.params.rsi_overbought,
                "rsi_oversold": self.params.rsi_oversold,
                "sma_short": self.params.sma_short,
                "sma_medium": self.params.sma_medium,
                "sma_long": self.params.sma_long,
            }
        )

    def run(
        self,
        ticker: str,
        df: pd.DataFrame,
        initial_investment: float = 10_000.0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[SimulationResult]:
        """
        Run simulation on historical OHLCV data.

        Args:
            ticker: stock symbol
            df: OHLCV DataFrame (indexed by date)
            initial_investment: starting portfolio value
            start_date / end_date: ISO date strings to slice the period

        Returns:
            SimulationResult or None on failure
        """
        if df is None or len(df) < 60:
            logger.warning("Insufficient data for simulation (%d rows)", len(df) if df is not None else 0)
            return None

        # ── Slice date range ──────────────────────────────────────────────────
        if start_date:
            df = df[df.index >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df.index <= pd.Timestamp(end_date)]
        if len(df) < 30:
            return None

        # ── Pre-compute all indicators ────────────────────────────────────────
        idf = compute_all(df, {
            "rsi_period": self.params.rsi_period,
            "sma_short": self.params.sma_short,
            "sma_medium": self.params.sma_medium,
            "sma_long": self.params.sma_long,
            "macd_fast": self.params.macd_fast,
            "macd_slow": self.params.macd_slow,
            "macd_signal": self.params.macd_signal,
        })
        idf = idf.dropna(subset=["rsi", "sma_short", "sma_medium"])

        # ── State ─────────────────────────────────────────────────────────────
        cash = float(initial_investment)
        shares = 0.0
        entry_price = 0.0
        entry_date = ""
        in_trade = False
        trades: List[TradeRecord] = []
        equity_curve: List[Dict] = []

        stop_loss_price = 0.0
        take_profit_price = 0.0

        # ── Bar loop ──────────────────────────────────────────────────────────
        for i in range(len(idf)):
            bar_df = idf.iloc[: i + 1]
            bar = idf.iloc[i]
            price = float(bar["close"])
            date_str = bar.name.strftime("%Y-%m-%d") if hasattr(bar.name, "strftime") else str(bar.name)

            # ── Check stop-loss / take-profit ──────────────────────────────
            if in_trade:
                exit_reason = None
                if self.params.stop_loss_pct > 0 and price <= stop_loss_price:
                    exit_reason = "stop_loss"
                elif self.params.take_profit_pct > 0 and price >= take_profit_price:
                    exit_reason = "take_profit"

                if exit_reason:
                    trade = self._close_trade(
                        cash, shares, entry_price, price, entry_date, date_str, exit_reason
                    )
                    cash = trade.shares * price + (cash - trade.shares * entry_price) + trade.pnl
                    shares = 0.0
                    in_trade = False
                    trades.append(trade)

            # ── Generate signal ───────────────────────────────────────────
            signal = self._signal_engine.analyse_row(ticker, bar_df)
            if signal is None:
                equity_val = cash + shares * price
                equity_curve.append({"date": date_str, "value": equity_val})
                continue

            # ── Execute signal ────────────────────────────────────────────
            if (
                not in_trade
                and signal.signal_type == "BUY"
                and signal.strength >= self.params.min_signal_strength
                and cash > 0
            ):
                invest = cash * (self.params.position_size_pct / 100.0)
                shares = invest / price
                entry_price = price
                entry_date = date_str
                cash -= invest
                in_trade = True
                stop_loss_price = price * (1 - self.params.stop_loss_pct / 100)
                take_profit_price = (
                    price * (1 + self.params.take_profit_pct / 100)
                    if self.params.take_profit_pct > 0
                    else float("inf")
                )

            elif (
                in_trade
                and signal.signal_type == "SELL"
                and signal.strength >= self.params.min_signal_strength
            ):
                trade = self._close_trade(
                    cash, shares, entry_price, price, entry_date, date_str, "signal"
                )
                cash = cash + shares * price
                shares = 0.0
                in_trade = False
                trades.append(trade)

            equity_val = cash + shares * price
            equity_curve.append({"date": date_str, "value": equity_val})

        # ── Close any open trade at end of data ───────────────────────────────
        if in_trade and shares > 0:
            final_price = float(idf.iloc[-1]["close"])
            final_date = idf.index[-1].strftime("%Y-%m-%d")
            trade = self._close_trade(
                cash, shares, entry_price, final_price, entry_date, final_date, "end_of_data"
            )
            cash = cash + shares * final_price
            shares = 0.0
            trades.append(trade)

        final_value = cash + shares * (float(idf.iloc[-1]["close"]) if shares > 0 else 0)

        # ── Performance metrics ───────────────────────────────────────────────
        total_return_pct = (final_value - initial_investment) / initial_investment * 100
        max_dd = _max_drawdown([e["value"] for e in equity_curve])
        win_rate = (
            len([t for t in trades if t.pnl > 0]) / len(trades) * 100
            if trades
            else 0.0
        )
        sharpe = _sharpe_ratio([e["value"] for e in equity_curve])

        return SimulationResult(
            ticker=ticker,
            start_date=idf.index[0].strftime("%Y-%m-%d"),
            end_date=idf.index[-1].strftime("%Y-%m-%d"),
            initial_invest=round(initial_investment, 2),
            final_value=round(final_value, 2),
            total_return_pct=round(total_return_pct, 2),
            max_drawdown_pct=round(max_dd, 2),
            win_rate_pct=round(win_rate, 2),
            total_trades=len(trades),
            sharpe_ratio=round(sharpe, 3),
            trades=trades,
            equity_curve=equity_curve,
            strategy_params=self.params,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _close_trade(
        self,
        cash: float,
        shares: float,
        entry_price: float,
        exit_price: float,
        entry_date: str,
        exit_date: str,
        exit_reason: str,
    ) -> TradeRecord:
        gross = shares * exit_price
        cost = shares * entry_price
        pnl = gross - cost
        pnl_pct = pnl / cost * 100 if cost > 0 else 0.0
        return TradeRecord(
            entry_date=entry_date,
            exit_date=exit_date,
            entry_price=round(entry_price, 4),
            exit_price=round(exit_price, 4),
            shares=round(shares, 6),
            pnl=round(pnl, 2),
            pnl_pct=round(pnl_pct, 2),
            exit_reason=exit_reason,
        )


# ── Statistical helpers ───────────────────────────────────────────────────────

def _max_drawdown(equity: List[float]) -> float:
    if len(equity) < 2:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _sharpe_ratio(equity: List[float], risk_free: float = 0.02) -> float:
    if len(equity) < 2:
        return 0.0
    returns = np.diff(equity) / equity[:-1]
    daily_rf = risk_free / 252
    excess = returns - daily_rf
    std = np.std(excess)
    if std == 0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(252))
