"""
SmartTrade Insights - Dashboard Screen
Grid of up to 6 stock cards with live data and signals.
"""
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from app.analysis.signals import SignalEngine, Signal
from app.config import MAX_STOCKS, DEFAULT_REFRESH_INTERVAL
from app.data.data_manager import DataManager
from app.database.db_manager import DatabaseManager
from app.ui.stock_card import StockCard


class Dashboard(QWidget):
    """
    Main dashboard screen.
    Signals:
        open_chart(ticker)        – user clicked a stock card
        add_stock_requested()     – user clicked the + slot
        remove_stock(ticker)      – user clicked × on a card
        refresh_requested()       – manual refresh triggered
    """

    open_chart = pyqtSignal(str)
    add_stock_requested = pyqtSignal()
    remove_stock = pyqtSignal(str)
    refresh_requested = pyqtSignal()

    def __init__(
        self,
        data_manager: DataManager,
        db: DatabaseManager,
        parent=None,
    ):
        super().__init__(parent)
        self._dm = data_manager
        self._db = db
        self._cards: Dict[str, StockCard] = {}
        self._signal_engine = SignalEngine()

        self._build_ui()
        self._connect_signals()
        self._load_watchlist()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ── Header bar ────────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("DASHBOARD")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #8b949e; letter-spacing: 2px;")
        header.addWidget(title)

        header.addStretch()

        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        header.addWidget(self._status_lbl)

        self._refresh_btn = QPushButton("⟳")
        self._refresh_btn.setObjectName("refresh_btn")
        self._refresh_btn.setToolTip("Refresh all quotes")
        self._refresh_btn.setFixedSize(34, 28)
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        header.addWidget(self._refresh_btn)

        root.addLayout(header)

        # ── Market summary bar ────────────────────────────────────────────
        self._summary_bar = _SummaryBar()
        root.addWidget(self._summary_bar)

        # ── Card grid ─────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._grid_widget = QWidget()
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(12)

        scroll.setWidget(self._grid_widget)
        root.addWidget(scroll, stretch=1)

    def _connect_signals(self):
        self._dm.data_refreshed.connect(self._on_data_refreshed)
        self._dm.refresh_started.connect(self._on_refresh_started)
        self._dm.refresh_progress.connect(self._on_refresh_progress)

    # ── Watchlist management ──────────────────────────────────────────────────

    def _load_watchlist(self):
        """Rebuild cards from the DB watchlist."""
        # Clear existing
        for ticker, card in list(self._cards.items()):
            card.deleteLater()
        self._cards.clear()
        self._clear_grid()

        watchlist = self._db.get_watchlist()
        for entry in watchlist:
            self._add_card(entry["ticker"])

        # Fill remaining slots with "+" buttons
        self._fill_empty_slots()

    def refresh_watchlist(self):
        """Public: call after adding/removing tickers."""
        self._load_watchlist()

    def _add_card(self, ticker: str):
        if ticker in self._cards:
            return
        card = StockCard(ticker)
        card.clicked.connect(self.open_chart)
        card.remove.connect(self._on_remove_card)
        self._cards[ticker] = card

        # Populate with cached data if available
        quote = self._dm.get_cached_quote(ticker)
        if quote:
            card.update_quote(quote)

        # Company name from DB
        wl = {w["ticker"]: w for w in self._db.get_watchlist()}
        if ticker in wl and wl[ticker].get("name"):
            card.update_company_name(wl[ticker]["name"])

        # Latest signal from DB
        sig = self._db.get_latest_signal(ticker)
        if sig:
            card.update_signal(sig["signal_type"], sig["strength"] or 50.0, sig.get("rsi"))

        self._rebuild_grid()

    def _rebuild_grid(self):
        self._clear_grid()
        tickers = list(self._cards.keys())
        COLS = 3
        for i, ticker in enumerate(tickers):
            row, col = divmod(i, COLS)
            self._grid.addWidget(self._cards[ticker], row, col)
        self._fill_empty_slots()

    def _fill_empty_slots(self):
        used = len(self._cards)
        COLS = 3
        for slot in range(used, MAX_STOCKS):
            row, col = divmod(slot, COLS)
            btn = _AddSlotButton()
            btn.clicked.connect(self.add_stock_requested)
            self._grid.addWidget(btn, row, col)

    def _clear_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget() and not isinstance(item.widget(), StockCard):
                item.widget().deleteLater()

    def _on_remove_card(self, ticker: str):
        self.remove_stock.emit(ticker)

    # ── Refresh callbacks ─────────────────────────────────────────────────────

    def _on_refresh_clicked(self):
        self.refresh_requested.emit()
        self._dm.start_refresh()

    def _on_refresh_started(self):
        self._refresh_btn.setText("⟳")
        self._refresh_btn.setEnabled(False)
        self._status_lbl.setText("Refreshing…")
        self._status_lbl.setStyleSheet("color: #58a6ff; font-size: 11px;")

    def _on_refresh_progress(self, current: int, total: int):
        self._status_lbl.setText(f"Refreshing {current}/{total}…")

    def _on_data_refreshed(self, results: Dict):
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("⟳")
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        self._status_lbl.setText(f"Updated {now}")
        self._status_lbl.setStyleSheet("color: #3fb950; font-size: 11px;")

        buy_count = sell_count = hold_count = 0

        for ticker, quote in results.items():
            if ticker not in self._cards:
                continue
            card = self._cards[ticker]
            card.update_quote(quote)

            # Run analysis + update signal
            df = self._dm.get_historical(ticker, period="1y", interval="1d")
            if df is not None and len(df) >= 50:
                signal = self._signal_engine.analyse(ticker, df)
                if signal:
                    card.update_signal(signal.signal_type, signal.strength, signal.rsi)
                    self._db.upsert_signal(signal.to_db_dict())
                    if signal.signal_type == "BUY":
                        buy_count += 1
                    elif signal.signal_type == "SELL":
                        sell_count += 1
                    else:
                        hold_count += 1

            # Sparkline
            sparkline_data = self._dm.get_sparkline(ticker)
            if sparkline_data:
                card.update_sparkline(sparkline_data)

        self._summary_bar.update(buy_count, sell_count, hold_count, len(results))

        # Fade status back to neutral after 5 s
        QTimer.singleShot(5000, lambda: self._status_lbl.setStyleSheet(
            "color: #8b949e; font-size: 11px;"
        ))

    def update_card_sparklines(self):
        for ticker, card in self._cards.items():
            data = self._dm.get_sparkline(ticker)
            if data:
                card.update_sparkline(data)


# ── Supporting widgets ────────────────────────────────────────────────────────

class _AddSlotButton(QPushButton):
    """Empty slot placeholder that invites the user to add a stock."""

    def __init__(self, parent=None):
        super().__init__("+", parent)
        self.setObjectName("add_stock_btn")
        self.setMinimumSize(220, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFont(QFont("Segoe UI", 32))
        self.setToolTip("Add a stock to your watchlist")


class _SummaryBar(QFrame):
    """Compact top bar showing overall portfolio signal summary."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setStyleSheet(
            "background-color: #161b22; border: 1px solid #21262d; border-radius: 6px;"
        )
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 0, 12, 0)
        h.setSpacing(20)

        self._buy_lbl = self._stat("BUY", "#3fb950", "0")
        self._sell_lbl = self._stat("SELL", "#f85149", "0")
        self._hold_lbl = self._stat("HOLD", "#d29922", "0")

        h.addWidget(self._make_heading())
        h.addStretch()

        for lbl in (self._buy_lbl, self._sell_lbl, self._hold_lbl):
            h.addWidget(lbl)

    def _make_heading(self):
        lbl = QLabel("SIGNALS:")
        lbl.setStyleSheet("color: #6e7681; font-size: 10px; letter-spacing: 1px;")
        return lbl

    def _stat(self, label: str, color: str, default: str) -> QLabel:
        lbl = QLabel(f"{label}: {default}")
        lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600;")
        return lbl

    def update(self, buy: int, sell: int, hold: int, total: int):
        self._buy_lbl.setText(f"BUY: {buy}")
        self._sell_lbl.setText(f"SELL: {sell}")
        self._hold_lbl.setText(f"HOLD: {hold}")
