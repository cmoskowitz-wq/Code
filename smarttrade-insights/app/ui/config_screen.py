"""
SmartTrade Insights - Configuration Screen
Manage watchlist, API keys, refresh settings, and alert preferences.
"""
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
    QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QScrollArea, QSizePolicy,
    QSlider, QSpacerItem, QSpinBox, QVBoxLayout, QWidget,
)

from app.config import MAX_STOCKS, REFRESH_OPTIONS
from app.data.data_manager import DataManager
from app.database.db_manager import DatabaseManager
from app.utils.crypto import get_api_key, store_api_key, delete_api_key


class ConfigScreen(QWidget):
    """
    Configuration panel.
    Signals:
        watchlist_changed()   – tickers were added or removed
        settings_changed()    – general settings updated
    """

    watchlist_changed = pyqtSignal()
    settings_changed = pyqtSignal()

    def __init__(self, data_manager: DataManager, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self._dm = data_manager
        self._db = db
        self._build_ui()
        self._load_settings()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(16)

        root.addWidget(self._build_watchlist_panel(), stretch=2)
        root.addWidget(self._build_settings_panel(), stretch=3)

    # ── Left: Watchlist panel ─────────────────────────────────────────────────

    def _build_watchlist_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        v = QVBoxLayout(panel)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        # Title
        title = QLabel("WATCHLIST")
        title.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: 600; letter-spacing: 2px;")
        v.addWidget(title)

        # Count badge
        self._count_lbl = QLabel(f"0 / {MAX_STOCKS} stocks")
        self._count_lbl.setStyleSheet("color: #6e7681; font-size: 11px;")
        v.addWidget(self._count_lbl)

        v.addWidget(self._make_divider())

        # Ticker list
        self._ticker_list = QListWidget()
        self._ticker_list.setStyleSheet(
            "QListWidget { background: #0d1117; border: 1px solid #21262d; "
            "border-radius: 6px; padding: 4px; }"
            "QListWidget::item { padding: 8px 4px; border-radius: 4px; color: #e6edf3; }"
            "QListWidget::item:selected { background-color: #1f6feb; }"
            "QListWidget::item:hover { background-color: #161b22; }"
        )
        self._ticker_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        v.addWidget(self._ticker_list, stretch=1)

        # Add ticker input
        add_row = QHBoxLayout()
        self._ticker_input = QLineEdit()
        self._ticker_input.setPlaceholderText("Enter ticker (e.g. AAPL)")
        self._ticker_input.setMaxLength(10)
        self._ticker_input.returnPressed.connect(self._on_add_ticker)
        self._ticker_input.setStyleSheet(
            "QLineEdit { text-transform: uppercase; }"
        )
        add_row.addWidget(self._ticker_input, stretch=1)

        self._add_btn = QPushButton("Add")
        self._add_btn.setObjectName("primary_btn")
        self._add_btn.setFixedWidth(60)
        self._add_btn.clicked.connect(self._on_add_ticker)
        add_row.addWidget(self._add_btn)
        v.addLayout(add_row)

        # Validation feedback
        self._add_status_lbl = QLabel("")
        self._add_status_lbl.setStyleSheet("font-size: 11px;")
        v.addWidget(self._add_status_lbl)

        # Remove button
        self._remove_btn = QPushButton("Remove Selected")
        self._remove_btn.setObjectName("danger_btn")
        self._remove_btn.clicked.connect(self._on_remove_ticker)
        v.addWidget(self._remove_btn)

        return panel

    # ── Right: Settings panel ─────────────────────────────────────────────────

    def _build_settings_panel(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(0, 0, 8, 0)
        v.setSpacing(14)

        v.addWidget(self._build_datasource_group())
        v.addWidget(self._build_refresh_group())
        v.addWidget(self._build_indicator_group())
        v.addWidget(self._build_alert_group())
        v.addStretch()

        scroll.setWidget(content)
        return scroll

    def _build_datasource_group(self) -> QGroupBox:
        grp = QGroupBox("Data Source")
        form = QFormLayout(grp)
        form.setSpacing(10)
        form.setContentsMargins(12, 16, 12, 12)

        # Source selector
        self._source_combo = QComboBox()
        self._source_combo.addItems(["yfinance (Yahoo Finance)", "Alpha Vantage"])
        self._source_combo.currentIndexChanged.connect(self._on_source_changed)
        form.addRow("Primary source:", self._source_combo)

        # Alpha Vantage key
        av_row = QHBoxLayout()
        self._av_key_input = QLineEdit()
        self._av_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._av_key_input.setPlaceholderText("Paste Alpha Vantage API key…")
        av_row.addWidget(self._av_key_input)

        self._av_show_btn = QPushButton("Show")
        self._av_show_btn.setFixedWidth(50)
        self._av_show_btn.setCheckable(True)
        self._av_show_btn.toggled.connect(
            lambda on: self._av_key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )
        av_row.addWidget(self._av_show_btn)

        self._av_save_btn = QPushButton("Save")
        self._av_save_btn.setObjectName("primary_btn")
        self._av_save_btn.setFixedWidth(50)
        self._av_save_btn.clicked.connect(self._on_save_av_key)
        av_row.addWidget(self._av_save_btn)

        av_widget = QWidget()
        av_widget.setLayout(av_row)
        form.addRow("Alpha Vantage key:", av_widget)

        self._av_status_lbl = QLabel("")
        self._av_status_lbl.setStyleSheet("font-size: 11px;")
        form.addRow("", self._av_status_lbl)

        return grp

    def _build_refresh_group(self) -> QGroupBox:
        grp = QGroupBox("Auto-Refresh")
        form = QFormLayout(grp)
        form.setSpacing(10)
        form.setContentsMargins(12, 16, 12, 12)

        self._refresh_combo = QComboBox()
        for label, _ in REFRESH_OPTIONS:
            self._refresh_combo.addItem(label)
        self._refresh_combo.currentIndexChanged.connect(self._on_refresh_changed)
        form.addRow("Refresh interval:", self._refresh_combo)

        self._autostart_chk = QCheckBox("Refresh on startup")
        form.addRow("", self._autostart_chk)

        return grp

    def _build_indicator_group(self) -> QGroupBox:
        grp = QGroupBox("Indicator Parameters")
        form = QFormLayout(grp)
        form.setSpacing(10)
        form.setContentsMargins(12, 16, 12, 12)

        def spin(lo, hi, val, step=1):
            s = QSpinBox()
            s.setRange(lo, hi)
            s.setValue(val)
            s.setSingleStep(step)
            return s

        def dspin(lo, hi, val, step=1.0, dec=1):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setValue(val)
            s.setSingleStep(step)
            s.setDecimals(dec)
            return s

        self._rsi_period = spin(5, 50, 14)
        self._rsi_ob = spin(55, 90, 70)
        self._rsi_os = spin(10, 45, 30)
        self._sma_short = spin(5, 50, 20)
        self._sma_medium = spin(20, 100, 50)
        self._sma_long = spin(100, 500, 200)
        self._min_strength = dspin(0, 100, 55.0, 5.0)

        form.addRow("RSI period:", self._rsi_period)
        form.addRow("RSI overbought:", self._rsi_ob)
        form.addRow("RSI oversold:", self._rsi_os)
        form.addRow("SMA short:", self._sma_short)
        form.addRow("SMA medium:", self._sma_medium)
        form.addRow("SMA long:", self._sma_long)
        form.addRow("Min signal strength:", self._min_strength)

        save_btn = QPushButton("Save Indicator Settings")
        save_btn.setObjectName("primary_btn")
        save_btn.clicked.connect(self._save_indicator_settings)
        form.addRow("", save_btn)

        return grp

    def _build_alert_group(self) -> QGroupBox:
        grp = QGroupBox("Alerts & Notifications")
        form = QFormLayout(grp)
        form.setSpacing(10)
        form.setContentsMargins(12, 16, 12, 12)

        self._alert_signals_chk = QCheckBox("Desktop alert on new BUY/SELL signal")
        self._alert_signals_chk.setChecked(True)
        form.addRow("", self._alert_signals_chk)

        self._alert_strong_chk = QCheckBox("Only alert on Strong signals (≥70%)")
        form.addRow("", self._alert_strong_chk)

        save_btn = QPushButton("Save Alert Settings")
        save_btn.setObjectName("primary_btn")
        save_btn.clicked.connect(self._save_alert_settings)
        form.addRow("", save_btn)

        return grp

    # ── Watchlist operations ──────────────────────────────────────────────────

    def _refresh_ticker_list(self):
        self._ticker_list.clear()
        watchlist = self._db.get_watchlist()
        for entry in watchlist:
            item = QListWidgetItem()
            ticker = entry["ticker"]
            name = entry.get("name") or ""
            sector = entry.get("sector") or ""
            display = f"  {ticker}"
            if name:
                display += f"  ·  {name}"
            if sector:
                display += f"  ·  {sector}"
            item.setText(display)
            item.setData(Qt.ItemDataRole.UserRole, ticker)
            self._ticker_list.addItem(item)

        count = len(watchlist)
        self._count_lbl.setText(f"{count} / {MAX_STOCKS} stocks")
        color = "#f85149" if count >= MAX_STOCKS else "#8b949e"
        self._count_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        self._add_btn.setEnabled(count < MAX_STOCKS)

    def _on_add_ticker(self):
        ticker = self._ticker_input.text().strip().upper()
        if not ticker:
            return

        self._add_btn.setEnabled(False)
        self._add_btn.setText("…")
        self._add_status_lbl.setText("Validating ticker…")
        self._add_status_lbl.setStyleSheet("color: #58a6ff; font-size: 11px;")

        # Validation runs synchronously (fast_info is quick)
        from PyQt6.QtCore import QCoreApplication
        QCoreApplication.processEvents()

        ok, message = self._dm.validate_and_add_ticker(ticker)

        if ok:
            self._add_status_lbl.setText(f"✓ Added {ticker} – {message}")
            self._add_status_lbl.setStyleSheet("color: #3fb950; font-size: 11px;")
            self._ticker_input.clear()
            self._refresh_ticker_list()
            self.watchlist_changed.emit()
        else:
            self._add_status_lbl.setText(f"✗ {message}")
            self._add_status_lbl.setStyleSheet("color: #f85149; font-size: 11px;")

        self._add_btn.setEnabled(True)
        self._add_btn.setText("Add")

    def _on_remove_ticker(self):
        item = self._ticker_list.currentItem()
        if not item:
            return
        ticker = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self,
            "Remove Stock",
            f"Remove {ticker} from your watchlist?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.remove_ticker(ticker)
            self._refresh_ticker_list()
            self.watchlist_changed.emit()

    # ── Settings operations ───────────────────────────────────────────────────

    def _load_settings(self):
        self._refresh_ticker_list()
        settings = self._db.get_all_settings()

        # Data source
        source = settings.get("data_source", "yfinance")
        idx = 1 if source == "alphavantage" else 0
        self._source_combo.setCurrentIndex(idx)

        # Alpha Vantage key
        av_key = get_api_key("alphavantage_api_key")
        if av_key:
            self._av_key_input.setPlaceholderText("API key saved ✓")
            self._av_status_lbl.setText("Alpha Vantage key loaded")
            self._av_status_lbl.setStyleSheet("color: #3fb950; font-size: 11px;")
            self._dm.set_av_key(av_key)

        # Refresh interval
        interval_val = int(settings.get("refresh_interval", DEFAULT_REFRESH_INTERVAL))
        for i, (_, secs) in enumerate(REFRESH_OPTIONS):
            if secs == interval_val:
                self._refresh_combo.setCurrentIndex(i)
                break

        # Auto-start
        self._autostart_chk.setChecked(settings.get("autostart_refresh", "0") == "1")

        # Indicators
        self._rsi_period.setValue(int(settings.get("rsi_period", 14)))
        self._rsi_ob.setValue(int(settings.get("rsi_overbought", 70)))
        self._rsi_os.setValue(int(settings.get("rsi_oversold", 30)))
        self._sma_short.setValue(int(settings.get("sma_short", 20)))
        self._sma_medium.setValue(int(settings.get("sma_medium", 50)))
        self._sma_long.setValue(int(settings.get("sma_long", 200)))
        self._min_strength.setValue(float(settings.get("min_signal_strength", 55.0)))

        # Alerts
        self._alert_signals_chk.setChecked(settings.get("alert_on_signal", "1") == "1")
        self._alert_strong_chk.setChecked(settings.get("alert_strong_only", "0") == "1")

    def _on_source_changed(self, index: int):
        source = "alphavantage" if index == 1 else "yfinance"
        self._db.set_setting("data_source", source)
        self._dm.set_source(source)
        self.settings_changed.emit()

    def _on_refresh_changed(self, index: int):
        _, secs = REFRESH_OPTIONS[index]
        self._db.set_setting("refresh_interval", str(secs))
        self.settings_changed.emit()

    def _on_save_av_key(self):
        key = self._av_key_input.text().strip()
        if not key:
            return
        ok = store_api_key("alphavantage_api_key", key)
        if ok:
            self._dm.set_av_key(key)
            self._av_status_lbl.setText("Alpha Vantage key saved ✓")
            self._av_status_lbl.setStyleSheet("color: #3fb950; font-size: 11px;")
            self._av_key_input.clear()
            self._av_key_input.setPlaceholderText("API key saved ✓")
        else:
            self._av_status_lbl.setText("Failed to save key")
            self._av_status_lbl.setStyleSheet("color: #f85149; font-size: 11px;")

    def _save_indicator_settings(self):
        settings = {
            "rsi_period": str(self._rsi_period.value()),
            "rsi_overbought": str(self._rsi_ob.value()),
            "rsi_oversold": str(self._rsi_os.value()),
            "sma_short": str(self._sma_short.value()),
            "sma_medium": str(self._sma_medium.value()),
            "sma_long": str(self._sma_long.value()),
            "min_signal_strength": str(self._min_strength.value()),
        }
        for k, v in settings.items():
            self._db.set_setting(k, v)
        self.settings_changed.emit()

        msg = QLabel("Indicator settings saved ✓")
        msg.setStyleSheet("color: #3fb950;")
        QMessageBox.information(self, "Saved", "Indicator settings have been saved.")

    def _save_alert_settings(self):
        self._db.set_setting("alert_on_signal", "1" if self._alert_signals_chk.isChecked() else "0")
        self._db.set_setting("alert_strong_only", "1" if self._alert_strong_chk.isChecked() else "0")
        self.settings_changed.emit()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _make_divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #21262d;")
        line.setFixedHeight(1)
        return line
