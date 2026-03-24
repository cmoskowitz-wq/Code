"""
SmartTrade Insights - Alpha Vantage Data Provider
Optional secondary data source – requires a free API key from
https://www.alphavantage.co/support/#api-key
Free tier: 25 requests/day (upgraded free: 500/day).
"""
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

from app.config import ALPHA_VANTAGE_BASE_URL, ALPHA_VANTAGE_TIMEOUT

logger = logging.getLogger(__name__)

# Rate-limit guard for free tier (5 req/min)
_RATE_LIMIT_INTERVAL = 13  # seconds between calls
_last_call_time: float = 0.0


def _rate_limit():
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < _RATE_LIMIT_INTERVAL:
        time.sleep(_RATE_LIMIT_INTERVAL - elapsed)
    _last_call_time = time.time()


class AlphaVantageProvider:
    """Fetches market data from the Alpha Vantage REST API."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key

    @api_key.setter
    def api_key(self, value: str):
        self._api_key = value

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    # ── Internal HTTP helper ──────────────────────────────────────────────────

    def _get(self, params: Dict) -> Optional[Dict]:
        if not self._api_key:
            logger.warning("Alpha Vantage API key not set")
            return None
        _rate_limit()
        params["apikey"] = self._api_key
        try:
            resp = requests.get(
                ALPHA_VANTAGE_BASE_URL,
                params=params,
                timeout=ALPHA_VANTAGE_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            if "Error Message" in data:
                logger.error("AV error: %s", data["Error Message"])
                return None
            if "Note" in data:
                logger.warning("AV rate-limit note: %s", data["Note"])
                return None
            if "Information" in data:
                logger.warning("AV info: %s", data["Information"])
                return None
            return data
        except requests.RequestException as e:
            logger.error("Alpha Vantage request error: %s", e)
            return None

    # ── Public API ────────────────────────────────────────────────────────────

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Global Quote endpoint – current price + change."""
        data = self._get({"function": "GLOBAL_QUOTE", "symbol": ticker})
        if not data:
            return None
        q = data.get("Global Quote", {})
        if not q or not q.get("05. price"):
            return None
        price = float(q["05. price"])
        prev_close = float(q.get("08. previous close") or 0)
        change = float(q.get("09. change") or 0)
        change_pct_raw = q.get("10. change percent", "0%").replace("%", "")
        return {
            "ticker": ticker.upper(),
            "price": price,
            "prev_close": prev_close,
            "open": float(q.get("02. open") or 0),
            "high": float(q.get("03. high") or 0),
            "low": float(q.get("04. low") or 0),
            "change": change,
            "change_pct": float(change_pct_raw),
            "volume": int(q.get("06. volume") or 0),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "alphavantage",
        }

    def get_historical(
        self,
        ticker: str,
        outputsize: str = "full",  # "compact" = 100 bars, "full" = 20y
    ) -> Optional[pd.DataFrame]:
        """Daily adjusted OHLCV data."""
        data = self._get(
            {
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "outputsize": outputsize,
            }
        )
        if not data:
            return None
        ts = data.get("Time Series (Daily)", {})
        if not ts:
            return None

        records = []
        for date_str, values in ts.items():
            records.append(
                {
                    "date": pd.to_datetime(date_str),
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": float(values["4. close"]),
                    "volume": int(values["5. volume"]),
                }
            )
        df = pd.DataFrame(records).set_index("date").sort_index()
        return df

    def validate_ticker(self, ticker: str) -> Tuple[bool, str]:
        """Use the search endpoint to validate a ticker."""
        data = self._get({"function": "SYMBOL_SEARCH", "keywords": ticker})
        if not data:
            return False, ""
        matches = data.get("bestMatches", [])
        for m in matches:
            if m.get("1. symbol", "").upper() == ticker.upper():
                return True, m.get("2. name", ticker)
        return False, ""

    def df_to_records(self, ticker: str, df: pd.DataFrame) -> List[Dict]:
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
