"""
TradeMe — Professional Trading Dashboard
Run: python main.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Set Qt backend before any matplotlib import
os.environ.setdefault("QT_API", "pyqt6")
import matplotlib
matplotlib.use("QtAgg")

import mplfinance as mpf
import pandas as pd

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

import matplotlib.pyplot as plt

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QStatusBar, QVBoxLayout, QWidget,
)

from analysis import generate_signal
from workers import MarketDataWorker, NewsWorker

# ── Config ─────────────────────────────────────────────────────────────────────

CONFIG_FILE   = Path(__file__).parent / "config.json"
NEWS_API_KEY  = "eb76f17efb2040a7a2d7eec4652f9613"
REFRESH_MS    = 60_000   # 1 minute

DEFAULT_TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL"]

# ── Colour palette ─────────────────────────────────────────────────────────────

C = {
    "bg":       "#0a0e1a",
    "panel":    "#0f1520",
    "card":     "#141c2e",
    "border":   "#1e2d4a",
    "text":     "#e8edf5",
    "muted":    "#8899b4",
    "accent":   "#2979ff",
    "green":    "#00e676",
    "red":      "#ff1744",
    "yellow":   "#ffc400",
    "dim_green":"#1a3d2b",
    "dim_red":  "#3d1a1a",
}

# ── Global stylesheet ──────────────────────────────────────────────────────────

STYLESHEET = f"""
* {{
    font-family: "SF Pro Display", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}
QWidget {{
    background-color: {C["bg"]};
    color: {C["text"]};
}}
QSplitter::handle {{
    background-color: {C["border"]};
    width: 1px;
    height: 1px;
}}
/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 5px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C["border"]};
    border-radius: 2px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {C["border"]};
    border-radius: 2px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
/* ── List ── */
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
    padding: 2px;
}}
QListWidget::item {{
    border-radius: 6px;
    padding: 2px 4px;
    margin: 1px 0;
}}
QListWidget::item:selected {{
    background-color: {C["accent"]};
}}
QListWidget::item:hover:!selected {{
    background-color: {C["card"]};
}}
/* ── Inputs ── */
QLineEdit {{
    background-color: {C["card"]};
    border: 1px solid {C["border"]};
    border-radius: 6px;
    padding: 7px 10px;
    color: {C["text"]};
    selection-background-color: {C["accent"]};
}}
QLineEdit:focus {{
    border-color: {C["accent"]};
}}
/* ── Buttons ── */
QPushButton {{
    background-color: {C["accent"]};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover  {{ background-color: #448aff; }}
QPushButton:pressed {{ background-color: #1565c0; }}
QPushButton[role="danger"] {{
    background-color: transparent;
    border: 1px solid {C["red"]};
    color: {C["red"]};
}}
QPushButton[role="danger"]:hover  {{ background-color: {C["dim_red"]}; }}
QPushButton[role="secondary"] {{
    background-color: transparent;
    border: 1px solid {C["border"]};
    color: {C["muted"]};
}}
QPushButton[role="secondary"]:hover {{
    background-color: {C["card"]};
    color: {C["text"]};
}}
/* ── Status bar ── */
QStatusBar {{
    background-color: {C["panel"]};
    color: {C["muted"]};
    border-top: 1px solid {C["border"]};
    font-size: 11px;
    padding: 0 8px;
}}
QStatusBar::item {{ border: none; }}
"""

# ── mplfinance chart style ─────────────────────────────────────────────────────

MPF_STYLE = mpf.make_mpf_style(
    base_mpl_style="dark_background",
    marketcolors=mpf.make_marketcolors(
        up=C["green"],  down=C["red"],
        edge={"up": C["green"], "down": C["red"]},
        wick={"up": C["green"], "down": C["red"]},
        volume={"up": C["green"], "down": C["red"]},
    ),
    mavcolors=["#ffd54f", "#ef9a9a"],   # MA20=amber, MA50=pink-red
    gridcolor=C["border"],
    gridstyle="--",
    gridaxis="both",
    facecolor=C["bg"],
    figcolor=C["bg"],
    rc={
        "axes.labelcolor": C["muted"],
        "axes.edgecolor":  C["border"],
        "xtick.color":     C["muted"],
        "ytick.color":     C["muted"],
        "font.size":       9,
        "axes.titlecolor": C["muted"],
    },
)


def _build_chart(df: pd.DataFrame) -> "matplotlib.figure.Figure":
    df_plot = df.tail(90).copy()
    rsi_series = df_plot["RSI"]
    has_rsi = rsi_series.notna().sum() >= 10

    addplots = []
    if has_rsi:
        idx = df_plot.index
        addplots = [
            mpf.make_addplot(rsi_series, panel=2, color=C["accent"],
                             ylabel="RSI", width=1.5, ylim=(0, 100)),
            mpf.make_addplot(pd.Series(70.0, index=idx), panel=2,
                             color=C["red"], linestyle="--", width=0.7, alpha=0.5),
            mpf.make_addplot(pd.Series(30.0, index=idx), panel=2,
                             color=C["green"], linestyle="--", width=0.7, alpha=0.5),
        ]

    panel_ratios = (4, 1.2, 1.5) if has_rsi else (4, 1.5)

    fig, _ = mpf.plot(
        df_plot,
        type="candle",
        mav=(20, 50),
        volume=True,
        addplot=addplots,
        returnfig=True,
        style=MPF_STYLE,
        figsize=(10, 7),
        panel_ratios=panel_ratios,
        tight_layout=True,
        show_nontrading=False,
    )
    return fig


# ── Helper widgets ─────────────────────────────────────────────────────────────

class _Sep(QFrame):
    """Thin horizontal separator line."""
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {C['border']};")


class _SectionLabel(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(
            f"color: {C['muted']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.2px; padding: 10px 0 4px 0;"
        )


class TickerRow(QWidget):
    """Left-panel watchlist row: symbol + live price + % change."""

    def __init__(self, symbol: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(6)

        self._sym = QLabel(symbol)
        self._sym.setStyleSheet("font-weight: 700; font-size: 13px;")

        self._price = QLabel("—")
        self._pct   = QLabel("")

        for lbl in (self._price, self._pct):
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._price.setStyleSheet(f"color: {C['muted']}; font-size: 12px;")
        self._pct.setStyleSheet("font-size: 10px; font-weight: 700;")
        self._pct.setFixedWidth(54)

        right = QVBoxLayout()
        right.setSpacing(1)
        right.addWidget(self._price)
        right.addWidget(self._pct)

        layout.addWidget(self._sym)
        layout.addStretch()
        layout.addLayout(right)

    def refresh(self, price: float, pct: float) -> None:
        color = C["green"] if pct >= 0 else C["red"]
        arrow = "▲" if pct > 0 else "▼" if pct < 0 else ""
        self._price.setText(f"${price:,.2f}")
        self._price.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
        self._pct.setText(f"{arrow} {abs(pct):.2f}%")
        self._pct.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: 700;")


class SignalBadge(QLabel):
    _STYLES: dict[str, tuple[str, str]] = {
        "STRONG BUY":  (C["green"],  C["dim_green"]),
        "BUY":         ("#69f0ae",   "#0d2b1c"),
        "HOLD":        (C["yellow"], "#2e2600"),
        "SELL":        ("#ff5252",   "#2e0a0a"),
        "STRONG SELL": (C["red"],    C["dim_red"]),
    }

    def set_signal(self, signal: str, confidence: int) -> None:
        color, bg = self._STYLES.get(signal, (C["muted"], C["card"]))
        self.setText(f"  {signal}  ·  {confidence}%  ")
        self.setStyleSheet(
            f"color: {color}; background-color: {bg}; "
            f"border: 1px solid {color}; border-radius: 6px; "
            f"font-size: 14px; font-weight: 700; padding: 4px 14px;"
        )


class MetricTile(QFrame):
    """Small info card: label above value."""

    def __init__(self, label: str):
        super().__init__()
        self.setStyleSheet(
            f"QFrame {{ background-color: {C['card']}; "
            f"border: 1px solid {C['border']}; border-radius: 6px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 8)
        layout.setSpacing(2)

        self._lbl = QLabel(label.upper())
        self._lbl.setStyleSheet(
            f"color: {C['muted']}; font-size: 9px; font-weight: 700; letter-spacing: 0.5px;"
        )
        self._val = QLabel("—")
        self._val.setStyleSheet(f"color: {C['text']}; font-size: 14px; font-weight: 600;")
        layout.addWidget(self._lbl)
        layout.addWidget(self._val)

    def set(self, text: str, color: str | None = None) -> None:
        self._val.setText(text)
        self._val.setStyleSheet(
            f"color: {color or C['text']}; font-size: 14px; font-weight: 600;"
        )


class ChartPane(QWidget):
    """Manages the mplfinance canvas — swaps it out on each update."""

    def __init__(self):
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._canvas: FigureCanvas | None = None

        placeholder = QLabel("Select a ticker to load chart")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"color: {C['muted']}; font-size: 15px;")
        self._layout.addWidget(placeholder)
        self._placeholder = placeholder

    def update(self, df: pd.DataFrame) -> None:  # type: ignore[override]
        try:
            fig = _build_chart(df)
            new_canvas = FigureCanvas(fig)
            new_canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            if self._canvas is not None:
                self._layout.removeWidget(self._canvas)
                plt.close(self._canvas.figure)
                self._canvas.deleteLater()
            if self._placeholder.isVisible():
                self._placeholder.hide()
                self._layout.removeWidget(self._placeholder)
            self._canvas = new_canvas
            self._layout.addWidget(self._canvas)
        except Exception as exc:
            print(f"[chart] {exc}")


class NewsCard(QFrame):
    def __init__(self, article: dict):
        super().__init__()
        self.setStyleSheet(
            f"QFrame {{ background-color: {C['card']}; "
            f"border: 1px solid {C['border']}; border-radius: 8px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        sentiment = article.get("_sentiment", 0.0)
        link      = article.get("url", "")
        title     = article.get("title") or "Untitled"
        source    = article.get("source", {}).get("name", "")
        date      = (article.get("publishedAt") or "").split("T")[0]

        if sentiment > 0.05:
            sc, sl = C["green"],  "Positive"
        elif sentiment < -0.05:
            sc, sl = C["red"],    "Negative"
        else:
            sc, sl = C["yellow"], "Neutral"

        lbl_title = QLabel(
            f'<a href="{link}" style="color:{C["text"]}; text-decoration:none;">{title}</a>'
        )
        lbl_title.setOpenExternalLinks(True)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet("font-size: 13px; font-weight: 500; line-height: 1.5;")

        meta = QHBoxLayout()
        meta.setSpacing(8)
        for txt in (source, date):
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"color: {C['muted']}; font-size: 11px;")
            meta.addWidget(lbl)
        meta.addStretch()
        badge = QLabel(sl)
        badge.setStyleSheet(
            f"color: {sc}; font-size: 10px; font-weight: 700; "
            f"border: 1px solid {sc}; border-radius: 3px; padding: 0 5px;"
        )
        meta.addWidget(badge)

        bar = QProgressBar()
        bar.setRange(-100, 100)
        bar.setValue(int(sentiment * 100))
        bar.setTextVisible(False)
        bar.setFixedHeight(3)
        bar.setStyleSheet(
            f"QProgressBar {{ background: {C['border']}; border-radius: 2px; border: none; }}"
            f"QProgressBar::chunk {{ background: {sc}; border-radius: 2px; }}"
        )

        layout.addWidget(lbl_title)
        layout.addLayout(meta)
        layout.addWidget(bar)


# ── Main Window ────────────────────────────────────────────────────────────────

class TradingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TradeMe  ·  Professional Trading Dashboard")
        self.setGeometry(40, 40, 1920, 1060)
        self.setMinimumSize(1280, 720)

        self.stocks: list[str] = self._load_config()
        self.cache:  dict[str, pd.DataFrame] = {}
        self.rows:   dict[str, TickerRow]    = {}

        self._data_worker: MarketDataWorker | None = None
        self._news_worker: NewsWorker | None = None
        self._countdown = REFRESH_MS // 1000

        self._build_ui()
        QApplication.instance().setStyleSheet(STYLESHEET)  # type: ignore[union-attr]
        self._populate_list()
        self._fetch_all()
        self._start_timers()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_config(self) -> list[str]:
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            return list(DEFAULT_TICKERS)

    def _save_config(self) -> None:
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.stocks, f, indent=2)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        outer.addWidget(splitter)

        splitter.addWidget(self._make_left())
        splitter.addWidget(self._make_center())
        splitter.addWidget(self._make_right())
        splitter.setSizes([230, 1060, 420])
        splitter.setStretchFactor(1, 1)

        # Status bar
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._sb_left  = QLabel("Initializing…")
        self._sb_right = QLabel("")
        sb.addWidget(self._sb_left)
        sb.addPermanentWidget(self._sb_right)

        # Keyboard shortcut
        QShortcut(QKeySequence("F5"), self).activated.connect(self._fetch_all)

    # ── Left panel ────────────────────────────────────────────────────────────

    def _make_left(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(230)
        w.setStyleSheet(
            f"background-color: {C['panel']}; "
            f"border-right: 1px solid {C['border']};"
        )
        lo = QVBoxLayout(w)
        lo.setContentsMargins(14, 18, 14, 14)
        lo.setSpacing(6)

        # Branding
        logo = QLabel("TradeMe")
        logo.setStyleSheet(
            f"color: {C['accent']}; font-size: 22px; font-weight: 800; letter-spacing: 1px;"
        )
        sub = QLabel("PROFESSIONAL DASHBOARD")
        sub.setStyleSheet(
            f"color: {C['muted']}; font-size: 9px; font-weight: 700; "
            f"letter-spacing: 1.8px; margin-bottom: 4px;"
        )
        lo.addWidget(logo)
        lo.addWidget(sub)
        lo.addWidget(_Sep())

        lo.addWidget(_SectionLabel("Watchlist"))

        self._list = QListWidget()
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.itemClicked.connect(self._on_item_clicked)
        lo.addWidget(self._list)

        lo.addWidget(_Sep())
        lo.addWidget(_SectionLabel("Add Ticker"))

        add_row = QHBoxLayout()
        add_row.setSpacing(6)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Symbol, e.g. AMZN")
        self._input.returnPressed.connect(self._add_ticker)
        btn_add = QPushButton("+")
        btn_add.setFixedWidth(34)
        btn_add.clicked.connect(self._add_ticker)
        add_row.addWidget(self._input)
        add_row.addWidget(btn_add)
        lo.addLayout(add_row)

        btn_rm = QPushButton("Remove Selected")
        btn_rm.setProperty("role", "danger")
        btn_rm.clicked.connect(self._remove_ticker)
        lo.addWidget(btn_rm)

        return w

    # ── Center panel ─────────────────────────────────────────────────────────

    def _make_center(self) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.setContentsMargins(22, 18, 22, 14)
        lo.setSpacing(10)

        # ── Header row
        hdr = QHBoxLayout()
        hdr.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._lbl_sym   = QLabel("—")
        self._lbl_sym.setStyleSheet(
            f"color: {C['text']}; font-size: 30px; font-weight: 800; letter-spacing: 0.5px;"
        )
        self._lbl_price = QLabel("")
        self._lbl_price.setStyleSheet(
            f"color: {C['muted']}; font-size: 19px; font-weight: 600;"
        )
        title_col.addWidget(self._lbl_sym)
        title_col.addWidget(self._lbl_price)
        hdr.addLayout(title_col)
        hdr.addStretch()

        self._badge = SignalBadge()
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.hide()
        hdr.addWidget(self._badge)
        lo.addLayout(hdr)

        # ── Metric tiles
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(8)
        self._m = {}
        for key in ("Volume", "Day High", "Day Low", "MA 20", "RSI", "52W High"):
            tile = MetricTile(key)
            self._m[key] = tile
            metrics_row.addWidget(tile)
        lo.addLayout(metrics_row)

        # ── Chart
        self._chart = ChartPane()
        self._chart.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        lo.addWidget(self._chart, stretch=1)

        # ── Signal reasons panel
        self._reasons = QLabel("")
        self._reasons.setWordWrap(True)
        self._reasons.setStyleSheet(
            f"background-color: {C['card']}; color: {C['muted']}; "
            f"font-size: 12px; padding: 10px 14px; border-radius: 6px; "
            f"border: 1px solid {C['border']}; line-height: 1.7;"
        )
        self._reasons.hide()
        lo.addWidget(self._reasons)

        return w

    # ── Right panel ───────────────────────────────────────────────────────────

    def _make_right(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(400)
        w.setStyleSheet(
            f"background-color: {C['panel']}; "
            f"border-left: 1px solid {C['border']};"
        )
        lo = QVBoxLayout(w)
        lo.setContentsMargins(14, 18, 14, 14)
        lo.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.addWidget(_SectionLabel("News Feed"))
        hdr.addStretch()
        self._news_sym = QLabel("")
        self._news_sym.setStyleSheet(
            f"color: {C['accent']}; font-weight: 700; font-size: 13px;"
        )
        hdr.addWidget(self._news_sym)
        lo.addLayout(hdr)
        lo.addWidget(_Sep())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        self._news_inner = QWidget()
        self._news_inner.setStyleSheet("background: transparent;")
        self._news_lo = QVBoxLayout(self._news_inner)
        self._news_lo.setContentsMargins(0, 0, 2, 0)
        self._news_lo.setSpacing(8)
        self._news_lo.addStretch()

        scroll.setWidget(self._news_inner)
        lo.addWidget(scroll)
        return w

    # ── Populate watchlist ────────────────────────────────────────────────────

    def _populate_list(self) -> None:
        self._list.clear()
        self.rows.clear()
        for symbol in self.stocks:
            self._insert_row(symbol)

    def _insert_row(self, symbol: str) -> None:
        item   = QListWidgetItem(self._list)
        widget = TickerRow(symbol)
        item.setSizeHint(widget.sizeHint())
        self._list.addItem(item)
        self._list.setItemWidget(item, widget)
        self.rows[symbol] = widget

    # ── Data fetch ────────────────────────────────────────────────────────────

    def _fetch_all(self) -> None:
        if self._data_worker and self._data_worker.isRunning():
            return
        self._sb_left.setText("Fetching market data…")
        self._data_worker = MarketDataWorker(self.stocks)
        self._data_worker.data_ready.connect(self._on_data)
        self._data_worker.all_done.connect(self._on_fetch_done)
        self._data_worker.error.connect(
            lambda sym, msg: print(f"[data] {sym}: {msg}")
        )
        self._data_worker.start()

    def _on_data(self, symbol: str, df: "pd.DataFrame") -> None:
        self.cache[symbol] = df
        latest = df.iloc[-1]
        prev   = df.iloc[-2] if len(df) > 1 else latest
        price  = latest["Close"]
        pct    = ((price - prev["Close"]) / prev["Close"] * 100) if prev["Close"] else 0

        if symbol in self.rows:
            self.rows[symbol].refresh(price, pct)

        # Auto-select the first symbol once its data lands
        if self._list.currentRow() < 0 and symbol == self.stocks[0]:
            self._list.setCurrentRow(0)
            self._display(symbol)

    def _on_fetch_done(self) -> None:
        self._sb_left.setText(
            f"Updated  {pd.Timestamp.now().strftime('%H:%M:%S')}"
        )
        self._countdown = REFRESH_MS // 1000
        # Refresh the currently selected stock
        idx = self._list.currentRow()
        if 0 <= idx < len(self.stocks):
            self._display(self.stocks[idx])

    # ── Display selected stock ────────────────────────────────────────────────

    def _on_item_clicked(self) -> None:
        idx = self._list.currentRow()
        if 0 <= idx < len(self.stocks):
            self._display(self.stocks[idx])

    def _display(self, symbol: str) -> None:
        df = self.cache.get(symbol)
        if df is None or df.empty:
            return

        latest     = df.iloc[-1]
        prev       = df.iloc[-2] if len(df) > 1 else latest
        price      = latest["Close"]
        prev_price = prev["Close"]
        pct        = ((price - prev_price) / prev_price * 100) if prev_price else 0
        color      = C["green"] if pct >= 0 else C["red"]
        arrow      = "▲" if pct > 0 else "▼" if pct < 0 else ""

        self._lbl_sym.setText(symbol)
        self._lbl_price.setText(f"${price:,.2f}   {arrow}  {pct:+.2f}%")
        self._lbl_price.setStyleSheet(
            f"color: {color}; font-size: 19px; font-weight: 600;"
        )

        # Signal badge
        signal, conf, reasons = generate_signal(df)
        self._badge.set_signal(signal, conf)
        self._badge.show()

        # Metric tiles
        vol    = latest.get("Volume", 0)
        ma20   = latest.get("MA20",   float("nan"))
        rsi    = latest.get("RSI",    float("nan"))
        hi52   = df["High"].max()
        rsi_color = (C["green"] if rsi < 30 else C["red"] if rsi > 70 else C["text"]) if pd.notna(rsi) else C["muted"]

        self._m["Volume"].set(f"{int(vol):,}" if vol else "—")
        self._m["Day High"].set(f"${latest['High']:,.2f}", C["green"])
        self._m["Day Low"].set(f"${latest['Low']:,.2f}", C["red"])
        self._m["MA 20"].set(f"${ma20:,.2f}" if pd.notna(ma20) else "—")
        self._m["RSI"].set(f"{rsi:.1f}" if pd.notna(rsi) else "—", rsi_color)
        self._m["52W High"].set(f"${hi52:,.2f}")

        # Chart (may take a moment — run synchronously but fast enough at 90 bars)
        self._chart.update(df)

        # Reasons
        bullet = "  •  "
        self._reasons.setText(bullet + f"\n{bullet}".join(reasons))
        self._reasons.show()

        # News
        self._fetch_news(symbol)

    # ── News ──────────────────────────────────────────────────────────────────

    def _fetch_news(self, symbol: str) -> None:
        if self._news_worker and self._news_worker.isRunning():
            self._news_worker.terminate()
        self._news_sym.setText(symbol)
        self._news_worker = NewsWorker(symbol, NEWS_API_KEY)
        self._news_worker.articles_ready.connect(self._on_news)
        self._news_worker.start()

    def _on_news(self, articles: list) -> None:
        # Remove all existing cards (everything except the trailing stretch)
        while self._news_lo.count() > 1:
            item = self._news_lo.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for article in articles:
            card = NewsCard(article)
            self._news_lo.insertWidget(self._news_lo.count() - 1, card)

    # ── Ticker management ─────────────────────────────────────────────────────

    def _add_ticker(self) -> None:
        symbol = self._input.text().strip().upper()
        if not symbol or symbol in self.stocks:
            self._input.clear()
            return
        self.stocks.append(symbol)
        self._insert_row(symbol)
        self._input.clear()
        self._save_config()
        self._fetch_all()

    def _remove_ticker(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self.stocks):
            return
        symbol = self.stocks.pop(row)
        self._list.takeItem(row)
        if symbol in self.rows:
            self.rows.pop(symbol).deleteLater()
        self.cache.pop(symbol, None)
        self._save_config()
        new_row = min(row, len(self.stocks) - 1)
        if new_row >= 0:
            self._list.setCurrentRow(new_row)
            self._on_item_clicked()

    # ── Timers ────────────────────────────────────────────────────────────────

    def _start_timers(self) -> None:
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._fetch_all)
        self._refresh_timer.start(REFRESH_MS)

        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._tick)
        self._countdown_timer.start(1_000)

    def _tick(self) -> None:
        self._countdown = max(0, self._countdown - 1)
        self._sb_right.setText(f"Refresh in  {self._countdown}s   F5 to refresh now")

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save_config()
        event.accept()


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("TradeMe")
    font = QFont("SF Pro Display", 13)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    window = TradingApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
