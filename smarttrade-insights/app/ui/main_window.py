"""
SmartTrade Insights - Main Application Window
Sidebar navigation shell that hosts Dashboard, Config, Simulation,
and a full-screen Chart overlay.
"""
import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QSizePolicy, QStackedWidget,
    QStatusBar, QVBoxLayout, QWidget,
)

from app.config import (
    APP_NAME, APP_VERSION,
    DEFAULT_REFRESH_INTERVAL,
    REFRESH_OPTIONS,
)
from app.data.data_manager import DataManager
from app.database.db_manager import DatabaseManager
from app.ui.chart_widget import ChartWidget
from app.ui.config_screen import ConfigScreen
from app.ui.dashboard import Dashboard
from app.ui.simulation_screen import SimulationScreen
from app.ui.styles import DARK_THEME

logger = logging.getLogger(__name__)

# ── Navigation page indices ───────────────────────────────────────────────────
PAGE_DASHBOARD = 0
PAGE_CONFIG = 1
PAGE_SIMULATION = 2
PAGE_CHART = 3


class MainWindow(QMainWindow):

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self._db = db
        self._dm = DataManager(db)
        self._refresh_timer = QTimer(self)
        self._refresh_interval = DEFAULT_REFRESH_INTERVAL

        self._build_ui()
        self._apply_theme()
        self._setup_refresh_timer()
        self._connect_signals()
        self._initial_load()

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1100, 700)
        self.resize(1400, 860)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content_area(), stretch=1)

        self._build_status_bar()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(64)

        v = QVBoxLayout(sidebar)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Logo area
        logo = QLabel("ST")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedHeight(56)
        logo.setStyleSheet(
            "color: #58a6ff; font-size: 16px; font-weight: 900; "
            "letter-spacing: 1px; border-bottom: 1px solid #21262d;"
        )
        v.addWidget(logo)

        # Nav buttons
        nav_items = [
            ("📊", "Dashboard", PAGE_DASHBOARD),
            ("⚙", "Settings", PAGE_CONFIG),
            ("📈", "Simulation", PAGE_SIMULATION),
        ]
        self._nav_buttons = {}
        for icon, tooltip, page in nav_items:
            btn = QPushButton(icon)
            btn.setObjectName("nav_btn")
            btn.setFixedSize(64, 56)
            btn.setToolTip(tooltip)
            btn.setFont(QFont("Segoe UI Emoji", 18))
            btn.clicked.connect(lambda _, p=page: self._navigate(p))
            self._nav_buttons[page] = btn
            v.addWidget(btn)

        v.addStretch()

        # Version label at bottom
        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setFixedHeight(32)
        ver_lbl.setStyleSheet("color: #6e7681; font-size: 9px;")
        v.addWidget(ver_lbl)

        return sidebar

    def _build_content_area(self) -> QStackedWidget:
        self._stack = QStackedWidget()

        # Dashboard
        self._dashboard = Dashboard(self._dm, self._db)
        self._stack.addWidget(self._dashboard)            # PAGE_DASHBOARD = 0

        # Config
        self._config = ConfigScreen(self._dm, self._db)
        self._stack.addWidget(self._config)              # PAGE_CONFIG = 1

        # Simulation
        self._simulation = SimulationScreen(self._dm, self._db)
        self._stack.addWidget(self._simulation)          # PAGE_SIMULATION = 2

        # Full chart (shown when clicking a stock card)
        self._chart = ChartWidget()
        self._chart.set_data_callback(
            lambda ticker, period, interval: self._dm.get_historical(ticker, period, interval)
        )
        self._stack.addWidget(self._chart)               # PAGE_CHART = 3

        return self._stack

    def _build_status_bar(self):
        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        self.setStatusBar(sb)

        self._sb_source_lbl = QLabel("yfinance")
        self._sb_source_lbl.setStyleSheet("color: #6e7681; padding: 0 8px;")
        sb.addPermanentWidget(self._sb_source_lbl)

        sep = QLabel("|")
        sep.setStyleSheet("color: #30363d;")
        sb.addPermanentWidget(sep)

        self._sb_refresh_lbl = QLabel("Auto-refresh: OFF")
        self._sb_refresh_lbl.setStyleSheet("color: #6e7681; padding: 0 8px;")
        sb.addPermanentWidget(self._sb_refresh_lbl)

        sep2 = QLabel("|")
        sep2.setStyleSheet("color: #30363d;")
        sb.addPermanentWidget(sep2)

        self._sb_time_lbl = QLabel("Ready")
        self._sb_time_lbl.setStyleSheet("color: #6e7681; padding: 0 8px;")
        sb.addPermanentWidget(self._sb_time_lbl)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _apply_theme(self):
        self.setStyleSheet(DARK_THEME)

    # ── Signals & slots ───────────────────────────────────────────────────────

    def _connect_signals(self):
        # Dashboard events
        self._dashboard.open_chart.connect(self._open_chart)
        self._dashboard.add_stock_requested.connect(lambda: self._navigate(PAGE_CONFIG))
        self._dashboard.remove_stock.connect(self._on_remove_stock)

        # Config events
        self._config.watchlist_changed.connect(self._on_watchlist_changed)
        self._config.settings_changed.connect(self._on_settings_changed)

        # DataManager events
        self._dm.data_refreshed.connect(self._on_data_refreshed)
        self._dm.refresh_started.connect(self._on_refresh_started)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+1"), self).activated.connect(
            lambda: self._navigate(PAGE_DASHBOARD)
        )
        QShortcut(QKeySequence("Ctrl+2"), self).activated.connect(
            lambda: self._navigate(PAGE_CONFIG)
        )
        QShortcut(QKeySequence("Ctrl+3"), self).activated.connect(
            lambda: self._navigate(PAGE_SIMULATION)
        )
        QShortcut(QKeySequence("Escape"), self).activated.connect(
            self._on_escape
        )
        QShortcut(QKeySequence("F5"), self).activated.connect(
            lambda: self._dm.start_refresh()
        )

    def _initial_load(self):
        """Load settings and start first refresh."""
        settings = self._db.get_all_settings()
        source = settings.get("data_source", "yfinance")
        self._dm.set_source(source)
        self._sb_source_lbl.setText(source.capitalize())

        interval = int(settings.get("refresh_interval", DEFAULT_REFRESH_INTERVAL))
        self._set_refresh_interval(interval)

        # Populate simulation ticker combo
        self._simulation.refresh_tickers()

        # Auto-start refresh
        autostart = settings.get("autostart_refresh", "0") == "1"
        if autostart:
            self._dm.start_refresh()

        # Navigate to dashboard
        self._navigate(PAGE_DASHBOARD)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _navigate(self, page: int):
        self._stack.setCurrentIndex(page)
        for p, btn in self._nav_buttons.items():
            active = (p == page)
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _open_chart(self, ticker: str):
        """Show the full chart for a ticker."""
        self._chart.load_ticker(ticker)
        self._navigate(PAGE_CHART)

    def _on_escape(self):
        if self._stack.currentIndex() == PAGE_CHART:
            self._navigate(PAGE_DASHBOARD)

    # ── Watchlist / settings change handlers ─────────────────────────────────

    def _on_watchlist_changed(self):
        self._dashboard.refresh_watchlist()
        self._simulation.refresh_tickers()
        # Kick off a refresh for newly added ticker
        self._dm.start_refresh()

    def _on_remove_stock(self, ticker: str):
        self._db.remove_ticker(ticker)
        self._dashboard.refresh_watchlist()
        self._simulation.refresh_tickers()

    def _on_settings_changed(self):
        settings = self._db.get_all_settings()
        interval = int(settings.get("refresh_interval", DEFAULT_REFRESH_INTERVAL))
        self._set_refresh_interval(interval)
        source = settings.get("data_source", "yfinance")
        self._sb_source_lbl.setText(source.capitalize())

    # ── Refresh timer ─────────────────────────────────────────────────────────

    def _setup_refresh_timer(self):
        self._refresh_timer.timeout.connect(self._dm.start_refresh)

    def _set_refresh_interval(self, seconds: int):
        self._refresh_interval = seconds
        self._refresh_timer.stop()
        if seconds > 0:
            self._refresh_timer.start(seconds * 1000)
            label = next(
                (l for l, s in REFRESH_OPTIONS if s == seconds),
                f"{seconds}s",
            )
            self._sb_refresh_lbl.setText(f"Auto-refresh: {label}")
        else:
            self._sb_refresh_lbl.setText("Auto-refresh: OFF")

    # ── Data callbacks ────────────────────────────────────────────────────────

    @pyqtSlot()
    def _on_refresh_started(self):
        self._sb_time_lbl.setText("Refreshing…")

    @pyqtSlot(dict)
    def _on_data_refreshed(self, results: dict):
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        self._sb_time_lbl.setText(f"Last updated: {now}")

    # ── Window close ─────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._dm.cancel_refresh()
        self._refresh_timer.stop()
        self._db.close()
        logger.info("Application closed")
        super().closeEvent(event)
