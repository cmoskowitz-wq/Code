"""
SmartTrade Insights - Application Configuration
"""
import os
from pathlib import Path

APP_NAME = "SmartTrade Insights"
APP_VERSION = "1.0.0"
APP_AUTHOR = "SmartTrade"

# ── Data directories ──────────────────────────────────────────────────────────
_appdata = os.getenv("APPDATA") or str(Path.home())
DATA_DIR = Path(_appdata) / "SmartTradeInsights"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "smarttrade.db"
LOG_PATH = DATA_DIR / "smarttrade.log"
EXPORT_DIR = DATA_DIR / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# ── Stock configuration ───────────────────────────────────────────────────────
MAX_STOCKS = 6
DEFAULT_REFRESH_INTERVAL = 300  # seconds (5 min)

# ── Technical indicator defaults ──────────────────────────────────────────────
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

SMA_SHORT = 20
SMA_MEDIUM = 50
SMA_LONG = 200

EMA_FAST = 12
EMA_SLOW = 26
MACD_SIGNAL = 9

BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2.0

MOMENTUM_PERIOD = 10

# ── Signal scoring weights ────────────────────────────────────────────────────
WEIGHT_RSI = 0.35
WEIGHT_MA_CROSS = 0.35
WEIGHT_MOMENTUM = 0.20
WEIGHT_VOLUME = 0.10

# Signal strength thresholds (0–100)
STRONG_SIGNAL_THRESHOLD = 70
MODERATE_SIGNAL_THRESHOLD = 50

# ── API configuration ─────────────────────────────────────────────────────────
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
ALPHA_VANTAGE_TIMEOUT = 15  # seconds
REQUEST_TIMEOUT = 10

# ── UI colours (dark terminal theme) ──────────────────────────────────────────
COLOR_BG_PRIMARY = "#0d1117"
COLOR_BG_SECONDARY = "#161b22"
COLOR_BG_TERTIARY = "#1c2128"
COLOR_BORDER = "#30363d"
COLOR_BORDER_FOCUS = "#58a6ff"

COLOR_TEXT_PRIMARY = "#e6edf3"
COLOR_TEXT_SECONDARY = "#8b949e"
COLOR_TEXT_MUTED = "#6e7681"

COLOR_BUY = "#3fb950"
COLOR_BUY_DIM = "#1a4d2e"
COLOR_SELL = "#f85149"
COLOR_SELL_DIM = "#4d1a1a"
COLOR_HOLD = "#d29922"
COLOR_HOLD_DIM = "#4d3a0a"

COLOR_ACCENT = "#58a6ff"
COLOR_ACCENT_DIM = "#1a3a5c"
COLOR_ACCENT_HOVER = "#79c0ff"

COLOR_CHART_PRICE = "#58a6ff"
COLOR_CHART_SMA_SHORT = "#f0883e"
COLOR_CHART_SMA_MEDIUM = "#d2a8ff"
COLOR_CHART_SMA_LONG = "#ffa657"
COLOR_CHART_VOLUME = "#2d3748"
COLOR_CHART_RSI = "#79c0ff"
COLOR_CHART_MACD = "#3fb950"
COLOR_CHART_SIGNAL = "#f0883e"

COLOR_POSITIVE = "#3fb950"
COLOR_NEGATIVE = "#f85149"
COLOR_NEUTRAL = "#8b949e"

# ── Chart settings ────────────────────────────────────────────────────────────
CHART_CANDLE_UP = "#3fb950"
CHART_CANDLE_DOWN = "#f85149"
CHART_CANDLE_WICK_UP = "#2d8a40"
CHART_CANDLE_WICK_DOWN = "#c43c35"

# ── Refresh interval options (label, seconds) ────────────────────────────────
REFRESH_OPTIONS = [
    ("Manual", 0),
    ("1 minute", 60),
    ("5 minutes", 300),
    ("15 minutes", 900),
    ("30 minutes", 1800),
]

# ── Historical data period options (label, yfinance period, yfinance interval) ─
HISTORY_OPTIONS = [
    ("1 Month",  "1mo",  "1d"),
    ("3 Months", "3mo",  "1d"),
    ("6 Months", "6mo",  "1d"),
    ("1 Year",   "1y",   "1d"),
    ("2 Years",  "2y",   "1wk"),
    ("5 Years",  "5y",   "1wk"),
]
