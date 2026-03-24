"""
SmartTrade Insights - SQLite Database Manager
"""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

from app.config import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages all SQLite database operations."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = str(db_path)
        self._connection: Optional[sqlite3.Connection] = None

    # ── Connection management ─────────────────────────────────────────────────

    def get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path, check_same_thread=False
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection

    @contextmanager
    def transaction(self):
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def initialize(self):
        """Create schema if it doesn't exist."""
        with self.transaction() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker      TEXT NOT NULL UNIQUE,
                    name        TEXT,
                    sector      TEXT,
                    position    INTEGER DEFAULT 0,
                    added_at    TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS price_data (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker      TEXT NOT NULL,
                    timestamp   TEXT NOT NULL,
                    open        REAL,
                    high        REAL,
                    low         REAL,
                    close       REAL NOT NULL,
                    volume      INTEGER,
                    interval    TEXT DEFAULT '1d',
                    UNIQUE(ticker, timestamp, interval)
                );
                CREATE INDEX IF NOT EXISTS idx_price_ticker_ts
                    ON price_data(ticker, timestamp);

                CREATE TABLE IF NOT EXISTS signals (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker      TEXT NOT NULL,
                    timestamp   TEXT NOT NULL,
                    signal_type TEXT NOT NULL,   -- BUY / SELL / HOLD
                    strength    REAL,            -- 0–100
                    rsi         REAL,
                    sma_short   REAL,
                    sma_medium  REAL,
                    sma_long    REAL,
                    macd        REAL,
                    macd_signal REAL,
                    momentum    REAL,
                    notes       TEXT,
                    UNIQUE(ticker, timestamp)
                );
                CREATE INDEX IF NOT EXISTS idx_signals_ticker
                    ON signals(ticker, timestamp);

                CREATE TABLE IF NOT EXISTS simulation_runs (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker           TEXT NOT NULL,
                    start_date       TEXT,
                    end_date         TEXT,
                    initial_invest   REAL,
                    final_value      REAL,
                    total_return_pct REAL,
                    max_drawdown_pct REAL,
                    win_rate_pct     REAL,
                    total_trades     INTEGER,
                    sharpe_ratio     REAL,
                    strategy_params  TEXT,  -- JSON blob
                    created_at       TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS simulation_trades (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id       INTEGER NOT NULL REFERENCES simulation_runs(id),
                    entry_date   TEXT,
                    exit_date    TEXT,
                    entry_price  REAL,
                    exit_price   REAL,
                    shares       REAL,
                    pnl          REAL,
                    pnl_pct      REAL,
                    trade_type   TEXT DEFAULT 'LONG'
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key     TEXT PRIMARY KEY,
                    value   TEXT
                );
            """)
        logger.info("Database initialised at %s", self.db_path)

    # ── Watchlist ─────────────────────────────────────────────────────────────

    def get_watchlist(self) -> List[Dict]:
        conn = self.get_connection()
        rows = conn.execute(
            "SELECT * FROM watchlist ORDER BY position, added_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def add_ticker(self, ticker: str, name: str = "", sector: str = "") -> bool:
        try:
            position = self._next_position()
            with self.transaction() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO watchlist (ticker, name, sector, position) "
                    "VALUES (?, ?, ?, ?)",
                    (ticker.upper(), name, sector, position),
                )
            return True
        except Exception as e:
            logger.error("add_ticker error: %s", e)
            return False

    def remove_ticker(self, ticker: str):
        with self.transaction() as conn:
            conn.execute("DELETE FROM watchlist WHERE ticker=?", (ticker.upper(),))

    def update_ticker_info(self, ticker: str, name: str, sector: str):
        with self.transaction() as conn:
            conn.execute(
                "UPDATE watchlist SET name=?, sector=? WHERE ticker=?",
                (name, sector, ticker.upper()),
            )

    def reorder_watchlist(self, ordered_tickers: List[str]):
        with self.transaction() as conn:
            for pos, ticker in enumerate(ordered_tickers):
                conn.execute(
                    "UPDATE watchlist SET position=? WHERE ticker=?",
                    (pos, ticker.upper()),
                )

    def _next_position(self) -> int:
        conn = self.get_connection()
        row = conn.execute("SELECT MAX(position) FROM watchlist").fetchone()
        return (row[0] or 0) + 1

    # ── Price data ────────────────────────────────────────────────────────────

    def upsert_price_data(self, ticker: str, rows: List[Dict], interval: str = "1d"):
        with self.transaction() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO price_data "
                "(ticker, timestamp, open, high, low, close, volume, interval) "
                "VALUES (:ticker, :timestamp, :open, :high, :low, :close, :volume, :interval)",
                [
                    {
                        "ticker": ticker.upper(),
                        "interval": interval,
                        **r,
                    }
                    for r in rows
                ],
            )

    def get_price_data(
        self,
        ticker: str,
        limit: int = 500,
        interval: str = "1d",
    ) -> List[Dict]:
        conn = self.get_connection()
        rows = conn.execute(
            "SELECT * FROM price_data "
            "WHERE ticker=? AND interval=? "
            "ORDER BY timestamp DESC LIMIT ?",
            (ticker.upper(), interval, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def get_latest_price(self, ticker: str) -> Optional[Dict]:
        conn = self.get_connection()
        row = conn.execute(
            "SELECT * FROM price_data WHERE ticker=? AND interval='1d' "
            "ORDER BY timestamp DESC LIMIT 1",
            (ticker.upper(),),
        ).fetchone()
        return dict(row) if row else None

    def purge_old_price_data(self, days: int = 365 * 5):
        """Remove price data older than N days."""
        with self.transaction() as conn:
            conn.execute(
                "DELETE FROM price_data WHERE timestamp < date('now', ?)",
                (f"-{days} days",),
            )

    # ── Signals ───────────────────────────────────────────────────────────────

    def upsert_signal(self, data: Dict):
        with self.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO signals "
                "(ticker, timestamp, signal_type, strength, rsi, sma_short, "
                " sma_medium, sma_long, macd, macd_signal, momentum, notes) "
                "VALUES (:ticker, :timestamp, :signal_type, :strength, :rsi, "
                "        :sma_short, :sma_medium, :sma_long, :macd, "
                "        :macd_signal, :momentum, :notes)",
                data,
            )

    def get_latest_signal(self, ticker: str) -> Optional[Dict]:
        conn = self.get_connection()
        row = conn.execute(
            "SELECT * FROM signals WHERE ticker=? ORDER BY timestamp DESC LIMIT 1",
            (ticker.upper(),),
        ).fetchone()
        return dict(row) if row else None

    def get_signal_history(self, ticker: str, limit: int = 100) -> List[Dict]:
        conn = self.get_connection()
        rows = conn.execute(
            "SELECT * FROM signals WHERE ticker=? ORDER BY timestamp DESC LIMIT ?",
            (ticker.upper(), limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_setting(self, key: str, default: Any = None) -> Any:
        conn = self.get_connection()
        row = conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: Any):
        with self.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )

    def get_all_settings(self) -> Dict[str, str]:
        conn = self.get_connection()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}

    # ── Simulation runs ───────────────────────────────────────────────────────

    def save_simulation_run(self, run: Dict) -> int:
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO simulation_runs "
                "(ticker, start_date, end_date, initial_invest, final_value, "
                " total_return_pct, max_drawdown_pct, win_rate_pct, "
                " total_trades, sharpe_ratio, strategy_params) "
                "VALUES (:ticker, :start_date, :end_date, :initial_invest, "
                "        :final_value, :total_return_pct, :max_drawdown_pct, "
                "        :win_rate_pct, :total_trades, :sharpe_ratio, "
                "        :strategy_params)",
                run,
            )
            return cur.lastrowid

    def save_simulation_trades(self, run_id: int, trades: List[Dict]):
        with self.transaction() as conn:
            conn.executemany(
                "INSERT INTO simulation_trades "
                "(run_id, entry_date, exit_date, entry_price, exit_price, "
                " shares, pnl, pnl_pct, trade_type) "
                "VALUES (:run_id, :entry_date, :exit_date, :entry_price, "
                "        :exit_price, :shares, :pnl, :pnl_pct, :trade_type)",
                [{"run_id": run_id, **t} for t in trades],
            )

    def get_simulation_history(self, ticker: str, limit: int = 20) -> List[Dict]:
        conn = self.get_connection()
        rows = conn.execute(
            "SELECT * FROM simulation_runs WHERE ticker=? "
            "ORDER BY created_at DESC LIMIT ?",
            (ticker.upper(), limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_simulation_trades(self, run_id: int) -> List[Dict]:
        conn = self.get_connection()
        rows = conn.execute(
            "SELECT * FROM simulation_trades WHERE run_id=? ORDER BY entry_date",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None
