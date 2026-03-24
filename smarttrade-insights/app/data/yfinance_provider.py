"""
SmartTrade Insights - Yahoo Finance Data Provider (via yfinance)
Primary data source – no API key required.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class YFinanceProvider:
    """Fetches market data from Yahoo Finance using the yfinance library."""

    # ── Public API ────────────────────────────────────────────────────────────

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Return current quote data for a ticker."""
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.fast_info

            # fast_info is a lightweight object; fall back to full info if needed
            price = getattr(info, "last_price", None)
            prev_close = getattr(info, "previous_close", None)
            open_price = getattr(info, "open", None)
            volume = getattr(info, "last_volume", None)
            market_cap = getattr(info, "market_cap", None)

            if price is None:
                return None

            change = (price - prev_close) if prev_close else 0.0
            change_pct = (change / prev_close * 100) if prev_close else 0.0

            return {
                "ticker": ticker.upper(),
                "price": round(price, 4),
                "prev_close": round(prev_close, 4) if prev_close else None,
                "open": round(open_price, 4) if open_price else None,
                "change": round(change, 4),
                "change_pct": round(change_pct, 4),
                "volume": int(volume) if volume else 0,
                "market_cap": market_cap,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "yfinance",
            }
        except Exception as e:
            logger.error("YFinance get_quote(%s) error: %s", ticker, e)
            return None

    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """Return company metadata."""
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            return {
                "name": info.get("longName") or info.get("shortName") or ticker,
                "sector": info.get("sector") or "",
                "industry": info.get("industry") or "",
                "description": info.get("longBusinessSummary") or "",
                "website": info.get("website") or "",
                "country": info.get("country") or "",
                "employees": info.get("fullTimeEmployees"),
                "pe_ratio": info.get("trailingPE"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "avg_volume": info.get("averageVolume"),
                "beta": info.get("beta"),
                "dividend_yield": info.get("dividendYield"),
            }
        except Exception as e:
            logger.warning("YFinance get_company_info(%s) error: %s", ticker, e)
            return {"name": ticker, "sector": ""}

    def get_historical(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> Optional[pd.DataFrame]:
        """
        Return OHLCV DataFrame indexed by datetime.
        period  : "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"
        interval: "1d", "1wk", "1mo"
        """
        try:
            import yfinance as yf
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
            if df.empty:
                logger.warning("YFinance returned empty DataFrame for %s", ticker)
                return None

            # Flatten MultiIndex columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df.columns = [c.lower() for c in df.columns]
            df.index = pd.to_datetime(df.index)
            df.index.name = "date"
            df = df.dropna(subset=["close"])
            return df
        except Exception as e:
            logger.error("YFinance get_historical(%s) error: %s", ticker, e)
            return None

    def get_intraday(
        self,
        ticker: str,
        interval: str = "5m",
        period: str = "1d",
    ) -> Optional[pd.DataFrame]:
        """Return intraday OHLCV data."""
        return self.get_historical(ticker, period=period, interval=interval)

    def validate_ticker(self, ticker: str) -> Tuple[bool, str]:
        """
        Returns (is_valid, company_name).
        A fast way to check without downloading full history.
        """
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.fast_info
            price = getattr(info, "last_price", None)
            if price and price > 0:
                full_info = t.info
                name = (
                    full_info.get("longName")
                    or full_info.get("shortName")
                    or ticker.upper()
                )
                return True, name
            return False, ""
        except Exception:
            return False, ""

    def df_to_records(self, ticker: str, df: pd.DataFrame) -> List[Dict]:
        """Convert a yfinance DataFrame to a list of dicts for DB storage."""
        records = []
        for ts, row in df.iterrows():
            records.append(
                {
                    "ticker": ticker.upper(),
                    "timestamp": ts.strftime("%Y-%m-%d"),
                    "open": round(float(row.get("open", 0) or 0), 6),
                    "high": round(float(row.get("high", 0) or 0), 6),
                    "low": round(float(row.get("low", 0) or 0), 6),
                    "close": round(float(row["close"]), 6),
                    "volume": int(row.get("volume", 0) or 0),
                }
            )
        return records
