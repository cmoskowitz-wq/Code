"""
SmartTrade Insights - Stock Card Widget
Displays a single stock's live data, signal, and sparkline chart.
"""
from typing import Dict, List, Optional

import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QCursor
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from app.config import (
    COLOR_BUY, COLOR_SELL, COLOR_HOLD, COLOR_ACCENT,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_BG_SECONDARY, COLOR_BORDER,
    CHART_CANDLE_UP, CHART_CANDLE_DOWN,
)
from app.ui.styles import signal_badge_style, change_color


class SparklineWidget(pg.PlotWidget):
    """Tiny inline price chart for a stock card."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground("#0d1117")
        self.setFixedHeight(55)
        self.hideAxis("left")
        self.hideAxis("bottom")
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)
        self.viewport().setProperty("cursor", QCursor(Qt.CursorShape.ArrowCursor))

        for side in ("top", "right"):
            self.showAxis(side)
            ax = self.getAxis(side)
            ax.setStyle(showValues=False, tickLength=0)
            ax.setPen(pg.mkPen(color="#21262d", width=1))

        self._curve = self.plot(pen=pg.mkPen(color="#58a6ff", width=1.5))
        self._fill = pg.FillBetweenItem(
            self._curve,
            self.plot(pen=pg.mkPen(None)),
            brush=pg.mkBrush(QColor(88, 166, 255, 25)),
        )
        self.addItem(self._fill)

    def set_data(self, prices: List[float], positive: bool = True):
        if not prices:
            return
        colour = COLOR_BUY if positive else COLOR_SELL
        self._curve.setPen(pg.mkPen(color=colour, width=1.5))
        fill_color = QColor(63, 185, 80, 25) if positive else QColor(248, 81, 73, 25)
        self._fill.setBrushes(pg.mkBrush(fill_color), pg.mkBrush(None))
        x = list(range(len(prices)))
        self._curve.setData(x, prices)
        baseline = self.plot(x, [min(prices)] * len(prices), pen=pg.mkPen(None))
        self._fill.setCurves(self._curve, baseline)


class StockCard(QFrame):
    """
    Rich card widget for a single stock.
    Emits:
        clicked(ticker)   – card was clicked (open chart)
        remove(ticker)    – user hit the × button
    """

    clicked = pyqtSignal(str)
    remove = pyqtSignal(str)

    def __init__(self, ticker: str, parent=None):
        super().__init__(parent)
        self._ticker = ticker
        self._setObjectName("card")
        self._build_ui()
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _setObjectName(self, name: str):
        self.setObjectName(name)

    def _build_ui(self):
        self.setObjectName("card")
        self.setMinimumSize(220, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(8)

        # ── Header row: ticker / remove button ────────────────────────────
        header = QHBoxLayout()
        self._ticker_lbl = QLabel(self._ticker)
        self._ticker_lbl.setObjectName("ticker_label")
        self._ticker_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.addWidget(self._ticker_lbl)

        header.addStretch()
        self._signal_lbl = QLabel("--")
        self._signal_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self._signal_lbl)

        self._remove_btn = QPushButton("×")
        self._remove_btn.setFixedSize(22, 22)
        self._remove_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; "
            "color: #6e7681; font-size: 16px; font-weight: bold; }"
            "QPushButton:hover { color: #f85149; }"
        )
        self._remove_btn.clicked.connect(lambda: self.remove.emit(self._ticker))
        header.addWidget(self._remove_btn)
        outer.addLayout(header)

        # ── Company name ──────────────────────────────────────────────────
        self._name_lbl = QLabel("")
        self._name_lbl.setObjectName("stat_label")
        self._name_lbl.setWordWrap(False)
        font = QFont("Segoe UI", 10)
        self._name_lbl.setFont(font)
        outer.addWidget(self._name_lbl)

        # ── Price row ─────────────────────────────────────────────────────
        price_row = QHBoxLayout()
        self._price_lbl = QLabel("--")
        self._price_lbl.setObjectName("price_label")
        self._price_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        price_row.addWidget(self._price_lbl)
        price_row.addStretch()

        change_col = QVBoxLayout()
        self._change_lbl = QLabel("--")
        self._change_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self._change_pct_lbl = QLabel("--")
        self._change_pct_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        change_col.addWidget(self._change_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        change_col.addWidget(self._change_pct_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        price_row.addLayout(change_col)
        outer.addLayout(price_row)

        # ── Sparkline ─────────────────────────────────────────────────────
        self._sparkline = SparklineWidget()
        outer.addWidget(self._sparkline)

        # ── Bottom stats grid: RSI | Volume | Strength ───────────────────
        stats = QGridLayout()
        stats.setHorizontalSpacing(12)
        stats.setVerticalSpacing(2)

        def stat_pair(label_text: str, row: int, col: int):
            lbl = QLabel(label_text)
            lbl.setObjectName("stat_label")
            lbl.setFont(QFont("Segoe UI", 9))
            val = QLabel("--")
            val.setObjectName("stat_value")
            val.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            stats.addWidget(lbl, row * 2, col)
            stats.addWidget(val, row * 2 + 1, col)
            return val

        self._rsi_val = stat_pair("RSI", 0, 0)
        self._vol_val = stat_pair("VOLUME", 0, 1)
        self._strength_val = stat_pair("STRENGTH", 0, 2)
        outer.addLayout(stats)

        # ── Strength bar ──────────────────────────────────────────────────
        self._strength_bar = _MiniBar()
        outer.addWidget(self._strength_bar)

    # ── Data update ───────────────────────────────────────────────────────────

    def update_quote(self, quote: Dict):
        price = quote.get("price", 0.0)
        change = quote.get("change", 0.0)
        change_pct = quote.get("change_pct", 0.0)
        volume = quote.get("volume", 0)

        self._price_lbl.setText(f"${price:,.2f}")
        color = change_color(change_pct)
        sign = "+" if change >= 0 else ""
        self._change_lbl.setText(f"{sign}{change:+.2f}")
        self._change_lbl.setStyleSheet(f"color: {color};")
        self._change_pct_lbl.setText(f"{sign}{change_pct:.2f}%")
        self._change_pct_lbl.setStyleSheet(f"color: {color};")

        self._vol_val.setText(_fmt_volume(volume))

        # Card border colour follows signal polarity
        self._update_border(change_pct)

    def update_signal(self, signal_type: str, strength: float, rsi: Optional[float] = None):
        self._signal_lbl.setText(signal_type)
        self._signal_lbl.setStyleSheet(signal_badge_style(signal_type))

        if rsi is not None:
            self._rsi_val.setText(f"{rsi:.1f}")
            rsi_color = (
                "#f85149" if rsi >= 70 else "#3fb950" if rsi <= 30 else "#e6edf3"
            )
            self._rsi_val.setStyleSheet(f"color: {rsi_color};")

        self._strength_val.setText(f"{strength:.0f}%")
        strength_color = (
            "#3fb950" if strength >= 70
            else "#d29922" if strength >= 50
            else "#f85149"
        )
        self._strength_val.setStyleSheet(f"color: {strength_color};")
        self._strength_bar.set_value(strength / 100, signal_type)

    def update_company_name(self, name: str):
        # Truncate to fit card
        display = name if len(name) <= 28 else name[:25] + "…"
        self._name_lbl.setText(display)

    def update_sparkline(self, prices: List[float]):
        if len(prices) >= 2:
            positive = prices[-1] >= prices[0]
            self._sparkline.set_data(prices, positive=positive)

    def set_loading(self, loading: bool):
        if loading:
            self._price_lbl.setText("Loading…")
            self._price_lbl.setStyleSheet("color: #6e7681;")

    # ── Interaction ───────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._ticker)
        super().mousePressEvent(event)

    def _update_border(self, change_pct: float):
        color = "#3fb950" if change_pct >= 0 else "#f85149"
        self.setStyleSheet(
            f"QFrame#card {{ background-color: #161b22; border: 1px solid {color}40; "
            f"border-radius: 8px; }}"
            f"QFrame#card:hover {{ border: 1px solid {color}; }}"
        )


# ── Mini strength bar ─────────────────────────────────────────────────────────

class _MiniBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(4)
        self._value = 0.0
        self._color = "#d29922"

    def set_value(self, value: float, signal_type: str = "HOLD"):
        self._value = max(0.0, min(1.0, value))
        self._color = (
            "#3fb950" if signal_type == "BUY"
            else "#f85149" if signal_type == "SELL"
            else "#d29922"
        )
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QBrush
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        # Background
        painter.fillRect(0, 0, w, h, QColor("#21262d"))
        # Fill
        fill_w = int(w * self._value)
        if fill_w > 0:
            painter.fillRect(0, 0, fill_w, h, QColor(self._color))
        painter.end()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_volume(vol: int) -> str:
    if vol >= 1_000_000_000:
        return f"{vol / 1_000_000_000:.1f}B"
    if vol >= 1_000_000:
        return f"{vol / 1_000_000:.1f}M"
    if vol >= 1_000:
        return f"{vol / 1_000:.0f}K"
    return str(vol)
