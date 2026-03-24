"""
SmartTrade Insights - Data Manager
Orchestrates data fetching, caching, and storage across providers.
Runs background refresh in a QThread to keep the UI responsive.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from app.config import (
    MAX_STOCKS,
    DEFAULT_REFRESH_INTERVAL,
    HISTORY_OPTIONS,
)
from app.data.yfinance_provider import YFinanceProvider
from app.data.alphavantage_provider import AlphaVantageProvider
from app.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


# ── Background worker ─────────────────────────────────────────────────────────

class RefreshWorker(QObject):
    """Runs in a QThread – fetches data for all watched tickers."""

    finished = pyqtSignal(dict)   # {ticker: quote_dict}
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)  # (current, total)

    def __init__(self, tickers: List[str], data_mgr: "DataManager"):
        super().__init__()
        self._tickers = tickers
        self._mgr = data_mgr
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @pyqtSlot()
    def run(self):
        results = {}
        total = len(self._tickers)
        for i, ticker in enumerate(self._tickers):
            if self._cancelled:
                break
            self.progress.emit(i + 1, total)
            try:
                quote = self._mgr.fetch_quote(ticker)
                if quote:
                    results[ticker] = quote
            except Exception as e:
                logger.error("RefreshWorker error for %s: %s", ticker, e)
        self.finished.emit(results)


# ── Data Manager ──────────────────────────────────────────────────────────────

class DataManager(QObject):
    """
    Central hub for all market data operations.
    Signals:
        data_refreshed  – emitted after a full refresh cycle completes
        quote_updated   – emitted when a single ticker's quote is fetched
        refresh_error   – emitted on fetch failure
        refresh_started – emitted when a refresh cycle begins
    """

    data_refreshed = pyqtSignal(dict)       # {ticker: quote}
    quote_updated = pyqtSignal(str, dict)   # (ticker, quote)
    refresh_error = pyqtSignal(str)
    refresh_started = pyqtSignal()
    refresh_progress = pyqtSignal(int, int)

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self._yf = YFinanceProvider()
        self._av = AlphaVantageProvider()
        self._source = "yfinance"  # "yfinance" | "alphavantage"

        self._thread: Optional[QThread] = None
        self._worker: Optional[RefreshWorker] = None
        self._quote_cache: Dict[str, Dict] = {}
        self._hist_cache: Dict[str, pd.DataFrame] = {}

    # ── Configuration ─────────────────────────────────────────────────────────

    def set_source(self, source: str):
        self._source = source

    def set_av_key(self, key: str):
        self._av.api_key = key

    @property
    def av_configured(self) -> bool:
        return self._av.is_configured

    # ── Quote fetching ────────────────────────────────────────────────────────

    def fetch_quote(self, ticker: str) -> Optional[Dict]:
        """Fetch current quote for one ticker, update cache + DB."""
        quote = None
        if self._source == "alphavantage" and self._av.is_configured:
            quote = self._av.get_quote(ticker)
        if quote is None:
            quote = self._yf.get_quote(ticker)

        if quote:
            self._quote_cache[ticker] = quote
        return quote

    def get_cached_quote(self, ticker: str) -> Optional[Dict]:
        return self._quote_cache.get(ticker)

    # ── Historical data ───────────────────────────────────────────────────────

    def get_historical(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        use_cache: bool = True,
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data.
        Checks in-memory cache first, then DB, then fetches from provider.
        """
        cache_key = f"{ticker}_{period}_{interval}"
        if use_cache and cache_key in self._hist_cache:
            return self._hist_cache[cache_key]

        # Try DB first (fast path for repeat requests)
        db_rows = self.db.get_price_data(ticker, limit=2000, interval=interval)
        if db_rows and len(db_rows) >= 20:
            df = _rows_to_df(db_rows)
            self._hist_cache[cache_key] = df
            return df

        # Fetch from provider
        df = self._fetch_and_store_historical(ticker, period, interval)
        if df is not None:
            self._hist_cache[cache_key] = df
        return df

    def _fetch_and_store_historical(
        self,
        ticker: str,
        period: str,
        interval: str,
    ) -> Optional[pd.DataFrame]:
        df = None
        if self._source == "alphavantage" and self._av.is_configured:
            df = self._av.get_historical(ticker)
        if df is None:
            df = self._yf.get_historical(ticker, period=period, interval=interval)

        if df is not None and not df.empty:
            provider = self._yf if df is not None else self._av
            records = self._yf.df_to_records(ticker, df)
            self.db.upsert_price_data(ticker, records, interval=interval)
        return df

    def refresh_historical(self, ticker: str, period: str = "1y", interval: str = "1d"):
        """Force-refresh historical data from provider."""
        cache_key = f"{ticker}_{period}_{interval}"
        self._hist_cache.pop(cache_key, None)
        return self._fetch_and_store_historical(ticker, period, interval)

    # ── Bulk refresh (background) ─────────────────────────────────────────────

    def start_refresh(self, tickers: Optional[List[str]] = None):
        """Start async refresh for all (or specified) tickers."""
        if self._thread and self._thread.isRunning():
            return  # already running

        if tickers is None:
            tickers = [w["ticker"] for w in self.db.get_watchlist()]

        if not tickers:
            return

        self.refresh_started.emit()
        self._thread = QThread()
        self._worker = RefreshWorker(tickers, self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_refresh_done)
        self._worker.error.connect(self.refresh_error)
        self._worker.progress.connect(self.refresh_progress)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_refresh_done(self, results: Dict):
        self._quote_cache.update(results)
        self.data_refreshed.emit(results)
        self._thread = None
        self._worker = None

    def cancel_refresh(self):
        if self._worker:
            self._worker.cancel()

    # ── Ticker validation ─────────────────────────────────────────────────────

    def validate_and_add_ticker(self, ticker: str) -> tuple[bool, str]:
        """Validate ticker, fetch company info, save to DB. Returns (ok, name)."""
        ticker = ticker.upper().strip()
        existing = [w["ticker"] for w in self.db.get_watchlist()]
        if ticker in existing:
            return False, "Already in watchlist"
        if len(existing) >= MAX_STOCKS:
            return False, f"Maximum {MAX_STOCKS} stocks allowed"

        valid, name = self._yf.validate_ticker(ticker)
        if not valid:
            return False, f"Ticker '{ticker}' not found"

        # Fetch company info for metadata
        info = self._yf.get_company_info(ticker)
        company_name = info.get("name", name) if info else name
        sector = info.get("sector", "") if info else ""

        self.db.add_ticker(ticker, name=company_name, sector=sector)
        return True, company_name

    # ── Sparkline helper ──────────────────────────────────────────────────────

    def get_sparkline(self, ticker: str, days: int = 30) -> List[float]:
        """Return the last N closing prices for a sparkline chart."""
        df = self.get_historical(ticker, period="1mo", interval="1d")
        if df is None or df.empty:
            return []
        closes = df["close"].dropna().tolist()
        return closes[-days:]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rows_to_df(rows: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("date").sort_index()
    for col in ("open", "high", "low", "close"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
    return df
