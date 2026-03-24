"""
SmartTrade Insights - Full Chart Widget
Multi-panel chart: candlesticks + MA overlays, volume bars, RSI panel.
Uses pyqtgraph for hardware-accelerated rendering.
"""
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from app.analysis.indicators import compute_all
from app.analysis.signals import SignalEngine
from app.config import (
    COLOR_CHART_PRICE, COLOR_CHART_SMA_SHORT, COLOR_CHART_SMA_MEDIUM,
    COLOR_CHART_SMA_LONG, COLOR_CHART_VOLUME, COLOR_CHART_RSI,
    CHART_CANDLE_UP, CHART_CANDLE_DOWN,
    COLOR_BUY, COLOR_SELL, COLOR_ACCENT,
    HISTORY_OPTIONS,
)

pg.setConfigOptions(antialias=True, foreground="#e6edf3", background="#0d1117")


# ── Candlestick item ──────────────────────────────────────────────────────────

class CandlestickItem(pg.GraphicsObject):
    """Custom pyqtgraph item for OHLC candlestick rendering."""

    def __init__(self):
        super().__init__()
        self._data = []
        self._picture = None

    def set_data(self, data: List[Dict]):
        """data: list of {t, open, high, low, close}"""
        self._data = data
        self._picture = None
        self.prepareGeometryChange()
        self.update()
        self.informViewBoundsChanged()

    def _build_picture(self):
        from PyQt6.QtGui import QPicture, QPainter, QPen, QBrush
        self._picture = QPicture()
        p = QPainter(self._picture)
        w = 0.4
        for d in self._data:
            t = d["t"]
            o, h, l, c = d["open"], d["high"], d["low"], d["close"]
            color = QColor(CHART_CANDLE_UP) if c >= o else QColor(CHART_CANDLE_DOWN)
            pen = pg.mkPen(color, width=1)
            p.setPen(pen)
            # Wick
            p.drawLine(pg.Point(t, l), pg.Point(t, h))
            # Body
            p.setBrush(pg.mkBrush(color))
            p.setPen(pg.mkPen(None))
            body_top = max(o, c)
            body_bot = min(o, c)
            body_h = max(body_top - body_bot, 0.001)
            p.drawRect(pg.QtCore.QRectF(t - w, body_bot, w * 2, body_h))
        p.end()

    def paint(self, p, *args):
        if not self._data:
            return
        if self._picture is None:
            self._build_picture()
        self._picture.play(p)

    def boundingRect(self):
        if not self._data:
            return pg.QtCore.QRectF()
        ts = [d["t"] for d in self._data]
        lows = [d["low"] for d in self._data]
        highs = [d["high"] for d in self._data]
        return pg.QtCore.QRectF(
            min(ts) - 0.5, min(lows),
            max(ts) - min(ts) + 1, max(highs) - min(lows),
        )


# ── Signal markers ────────────────────────────────────────────────────────────

class SignalMarker(pg.ScatterPlotItem):
    """Triangular buy/sell markers on the price chart."""

    @staticmethod
    def make_buy(xs: List[float], ys: List[float]) -> "SignalMarker":
        return pg.ScatterPlotItem(
            x=xs, y=ys,
            symbol="t1",  # up triangle
            size=12,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(COLOR_BUY),
        )

    @staticmethod
    def make_sell(xs: List[float], ys: List[float]) -> "SignalMarker":
        return pg.ScatterPlotItem(
            x=xs, y=ys,
            symbol="t",  # down triangle
            size=12,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(COLOR_SELL),
        )


# ── Main chart widget ─────────────────────────────────────────────────────────

class ChartWidget(QWidget):
    """
    Full multi-panel trading chart.
    Layout:
        [toolbar: ticker label | period buttons | indicator toggles]
        [price panel  75%]
        [volume panel 12%]
        [RSI panel    13%]
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ticker = ""
        self._df: Optional[pd.DataFrame] = None
        self._idf: Optional[pd.DataFrame] = None
        self._show_sma = True
        self._show_signals = True
        self._current_period = "1y"
        self._current_interval = "1d"
        self._signal_engine = SignalEngine()
        self._data_callback = None   # callable(ticker, period, interval) -> df
        self._build_ui()

    def set_data_callback(self, cb):
        """Register a callback to fetch historical data: cb(ticker, period, interval) -> df"""
        self._data_callback = cb

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_toolbar())
        layout.addWidget(self._build_chart_area(), stretch=1)

    def _build_toolbar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet(
            "background-color: #161b22; border-bottom: 1px solid #21262d;"
        )
        bar.setFixedHeight(44)
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 0, 12, 0)
        h.setSpacing(8)

        self._chart_ticker_lbl = QLabel("--")
        self._chart_ticker_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._chart_ticker_lbl.setStyleSheet("color: #e6edf3;")
        h.addWidget(self._chart_ticker_lbl)

        self._chart_price_lbl = QLabel("")
        self._chart_price_lbl.setFont(QFont("Segoe UI", 12))
        self._chart_price_lbl.setStyleSheet("color: #8b949e;")
        h.addWidget(self._chart_price_lbl)

        h.addStretch()

        # Period buttons
        self._period_btns: Dict[str, QPushButton] = {}
        for label, period, interval in HISTORY_OPTIONS:
            short = label.replace(" ", "").replace("Month", "M").replace("Months", "M").replace("Year", "Y").replace("Years", "Y")
            btn = QPushButton(short)
            btn.setFixedSize(40, 26)
            btn.setCheckable(True)
            btn.setStyleSheet(self._period_btn_style(False))
            btn.clicked.connect(lambda _, p=period, iv=interval, b=btn: self._on_period_click(p, iv, b))
            self._period_btns[period] = btn
            h.addWidget(btn)

        h.addSpacing(12)

        # Toggles
        self._sma_btn = self._toggle_btn("MA", True)
        self._sma_btn.clicked.connect(self._toggle_sma)
        h.addWidget(self._sma_btn)

        self._sig_btn = self._toggle_btn("SIG", True)
        self._sig_btn.clicked.connect(self._toggle_signals)
        h.addWidget(self._sig_btn)

        return bar

    def _build_chart_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        # Linked X axis
        self._price_plot = self._make_plot(height_hint=0.72)
        self._vol_plot = self._make_plot(height_hint=0.13, link_x=self._price_plot)
        self._rsi_plot = self._make_plot(height_hint=0.15, link_x=self._price_plot)

        self._price_plot.setMinimumHeight(300)
        self._vol_plot.setMaximumHeight(90)
        self._rsi_plot.setMaximumHeight(100)

        # Candles + MA + signal markers on price panel
        self._candle_item = CandlestickItem()
        self._price_plot.addItem(self._candle_item)

        self._sma_s_curve = self._price_plot.plot(pen=pg.mkPen(COLOR_CHART_SMA_SHORT, width=1.2), name="SMA20")
        self._sma_m_curve = self._price_plot.plot(pen=pg.mkPen(COLOR_CHART_SMA_MEDIUM, width=1.2), name="SMA50")
        self._sma_l_curve = self._price_plot.plot(pen=pg.mkPen(COLOR_CHART_SMA_LONG, width=1), name="SMA200")

        self._buy_markers = None
        self._sell_markers = None

        # Volume bars on volume panel
        self._vol_bars = pg.BarGraphItem(x=[], height=[], width=0.6, brushes=[])
        self._vol_plot.addItem(self._vol_bars)

        # RSI line on RSI panel
        self._rsi_curve = self._rsi_plot.plot(pen=pg.mkPen(COLOR_CHART_RSI, width=1.5), name="RSI")
        self._rsi_ob = pg.InfiniteLine(
            pos=70, angle=0,
            pen=pg.mkPen(color="#f85149", width=1, style=Qt.PenStyle.DashLine),
        )
        self._rsi_os = pg.InfiniteLine(
            pos=30, angle=0,
            pen=pg.mkPen(color="#3fb950", width=1, style=Qt.PenStyle.DashLine),
        )
        self._rsi_plot.addItem(self._rsi_ob)
        self._rsi_plot.addItem(self._rsi_os)
        self._rsi_plot.setYRange(0, 100, padding=0.05)

        # Crosshair
        self._vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#30363d", width=1))
        self._hline = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen("#30363d", width=1))
        self._price_plot.addItem(self._vline)
        self._price_plot.addItem(self._hline)
        self._price_plot.scene().sigMouseMoved.connect(self._on_mouse_move)

        # Legend
        legend = self._price_plot.addLegend(offset=(10, 10))
        legend.setParentItem(self._price_plot.graphicsItem())

        layout.addWidget(self._price_plot, stretch=72)
        layout.addWidget(self._vol_plot, stretch=13)
        layout.addWidget(self._rsi_plot, stretch=15)
        return container

    # ── Data loading ──────────────────────────────────────────────────────────

    def load_ticker(self, ticker: str, df: Optional[pd.DataFrame] = None):
        self._ticker = ticker
        self._chart_ticker_lbl.setText(ticker)
        if df is not None:
            self._set_dataframe(df)
        elif self._data_callback:
            new_df = self._data_callback(ticker, self._current_period, self._current_interval)
            if new_df is not None:
                self._set_dataframe(new_df)
        # Highlight active period button
        self._set_active_period_btn(self._current_period)

    def _set_dataframe(self, df: pd.DataFrame):
        self._df = df
        self._idf = compute_all(df)
        self._render()

    def _render(self):
        if self._idf is None or self._idf.empty:
            return

        idf = self._idf.reset_index()
        n = len(idf)
        x = np.arange(n, dtype=float)

        # ── Candlesticks ──────────────────────────────────────────────────
        candles = []
        for i, row in idf.iterrows():
            candles.append({
                "t": float(i),
                "open": float(row.get("open", row["close"])),
                "high": float(row.get("high", row["close"])),
                "low": float(row.get("low", row["close"])),
                "close": float(row["close"]),
            })
        self._candle_item.set_data(candles)

        # ── Moving averages ───────────────────────────────────────────────
        def _safe_series(col: str):
            if col not in idf.columns:
                return x, np.full(n, np.nan)
            vals = idf[col].values.astype(float)
            mask = ~np.isnan(vals)
            return x[mask], vals[mask]

        if self._show_sma:
            self._sma_s_curve.setData(*_safe_series("sma_short"))
            self._sma_m_curve.setData(*_safe_series("sma_medium"))
            self._sma_l_curve.setData(*_safe_series("sma_long"))
        else:
            for c in (self._sma_s_curve, self._sma_m_curve, self._sma_l_curve):
                c.setData([], [])

        # ── Buy/sell markers ──────────────────────────────────────────────
        for item in (self._buy_markers, self._sell_markers):
            if item and item.scene():
                self._price_plot.removeItem(item)

        if self._show_signals and len(idf) >= 50:
            signals = self._signal_engine.analyse(self._ticker, self._df)
            buy_xs, buy_ys, sell_xs, sell_ys = [], [], [], []
            for i2, row in idf.iterrows():
                sig = row.get("rsi", None)
                if sig is None:
                    continue
                rsi_val = float(sig)
                close = float(row["close"])
                if rsi_val <= 30:
                    buy_xs.append(float(i2))
                    buy_ys.append(float(row.get("low", close)) * 0.99)
                elif rsi_val >= 70:
                    sell_xs.append(float(i2))
                    sell_ys.append(float(row.get("high", close)) * 1.01)
            if buy_xs:
                self._buy_markers = SignalMarker.make_buy(buy_xs, buy_ys)
                self._price_plot.addItem(self._buy_markers)
            if sell_xs:
                self._sell_markers = SignalMarker.make_sell(sell_xs, sell_ys)
                self._price_plot.addItem(self._sell_markers)

        # ── Volume bars ───────────────────────────────────────────────────
        if "volume" in idf.columns:
            vols = idf["volume"].values.astype(float)
            closes = idf["close"].values.astype(float)
            opens = idf.get("open", idf["close"]).values.astype(float) if "open" in idf.columns else closes
            brushes = [
                pg.mkBrush("#3fb95060") if closes[i] >= opens[i] else pg.mkBrush("#f8514960")
                for i in range(n)
            ]
            self._vol_bars.setOpts(x=x, height=vols, width=0.6, brushes=brushes)

        # ── RSI ───────────────────────────────────────────────────────────
        if "rsi" in idf.columns:
            self._rsi_curve.setData(*_safe_series("rsi"))

        # ── Price label ───────────────────────────────────────────────────
        last_close = float(idf["close"].iloc[-1])
        self._chart_price_lbl.setText(f"${last_close:,.2f}")

        # ── X axis date ticks ─────────────────────────────────────────────
        if "date" in idf.columns:
            dates = idf["date"].dt.strftime("%b %d").tolist()
            step = max(1, n // 8)
            ticks = [(i, dates[i]) for i in range(0, n, step)]
            self._price_plot.getAxis("bottom").setTicks([ticks])

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_period_click(self, period: str, interval: str, btn: QPushButton):
        self._current_period = period
        self._current_interval = interval
        self._set_active_period_btn(period)
        if self._data_callback and self._ticker:
            df = self._data_callback(self._ticker, period, interval)
            if df is not None:
                self._set_dataframe(df)

    def _toggle_sma(self):
        self._show_sma = not self._show_sma
        self._sma_btn.setStyleSheet(self._period_btn_style(self._show_sma))
        self._render()

    def _toggle_signals(self):
        self._show_signals = not self._show_signals
        self._sig_btn.setStyleSheet(self._period_btn_style(self._show_signals))
        self._render()

    def _on_mouse_move(self, pos):
        if self._price_plot.sceneBoundingRect().contains(pos):
            mp = self._price_plot.plotItem.vb.mapSceneToView(pos)
            self._vline.setPos(mp.x())
            self._hline.setPos(mp.y())

    def _set_active_period_btn(self, period: str):
        for p, btn in self._period_btns.items():
            btn.setChecked(p == period)
            btn.setStyleSheet(self._period_btn_style(p == period))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_plot(self, height_hint: float = 1.0, link_x=None) -> pg.PlotWidget:
        pw = pg.PlotWidget()
        pw.setBackground("#0d1117")
        for side in ("top", "right"):
            pw.showAxis(side)
            pw.getAxis(side).setStyle(showValues=False, tickLength=0)
        for side in ("left", "bottom", "top", "right"):
            pw.getAxis(side).setPen(pg.mkPen("#21262d"))
            pw.getAxis(side).setTextPen(pg.mkPen("#6e7681"))
        pw.getAxis("bottom").setStyle(tickTextOffset=4)
        if link_x:
            pw.setXLink(link_x)
        return pw

    def _toggle_btn(self, label: str, active: bool) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedSize(40, 26)
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setStyleSheet(self._period_btn_style(active))
        return btn

    @staticmethod
    def _period_btn_style(active: bool) -> str:
        if active:
            return (
                "QPushButton { background-color: #1f6feb; color: #ffffff; "
                "border: 1px solid #1f6feb; border-radius: 4px; "
                "font-size: 11px; font-weight: 600; }"
            )
        return (
            "QPushButton { background-color: transparent; color: #8b949e; "
            "border: 1px solid #30363d; border-radius: 4px; "
            "font-size: 11px; font-weight: 600; }"
            "QPushButton:hover { color: #e6edf3; border-color: #58a6ff; }"
        )
