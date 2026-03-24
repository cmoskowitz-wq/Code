"""
SmartTrade Insights - Simulation / Backtesting Screen
Historical "what-if" analysis with equity curve, trade log, and metrics.
"""
import json
from typing import List, Optional

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QSlider, QSpinBox,
    QSplitter, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.config import HISTORY_OPTIONS
from app.data.data_manager import DataManager
from app.database.db_manager import DatabaseManager
from app.simulation.engine import SimulationEngine, SimulationResult, StrategyParams


# ── Background simulation worker ──────────────────────────────────────────────

class SimWorker(QObject):
    finished = pyqtSignal(object)  # SimulationResult | None
    error = pyqtSignal(str)

    def __init__(self, engine: SimulationEngine, ticker: str, df: pd.DataFrame,
                 initial: float, start_date: Optional[str], end_date: Optional[str]):
        super().__init__()
        self._engine = engine
        self._ticker = ticker
        self._df = df
        self._initial = initial
        self._start = start_date
        self._end = end_date

    @pyqtSlot()
    def run(self):
        try:
            result = self._engine.run(
                self._ticker, self._df, self._initial,
                start_date=self._start, end_date=self._end,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ── Simulation Screen ─────────────────────────────────────────────────────────

class SimulationScreen(QWidget):

    def __init__(self, data_manager: DataManager, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self._dm = data_manager
        self._db = db
        self._result: Optional[SimulationResult] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[SimWorker] = None
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("SIMULATION")
        title.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: 600; letter-spacing: 2px;")
        header.addWidget(title)
        header.addStretch()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        header.addWidget(self._status_lbl)
        root.addLayout(header)

        # Main splitter: controls | results
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_controls())
        splitter.addWidget(self._build_results())
        splitter.setSizes([280, 900])
        splitter.setHandleWidth(4)
        splitter.setStyleSheet("QSplitter::handle { background-color: #21262d; }")
        root.addWidget(splitter, stretch=1)

    # ── Controls panel ────────────────────────────────────────────────────────

    def _build_controls(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMaximumWidth(300)

        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(0, 0, 8, 0)
        v.setSpacing(12)

        # ── Simulation target ─────────────────────────────────────────────
        target_grp = QGroupBox("Target")
        form = QFormLayout(target_grp)
        form.setContentsMargins(12, 16, 12, 12)
        form.setSpacing(10)

        self._ticker_combo = QComboBox()
        self._ticker_combo.setMinimumWidth(120)
        form.addRow("Ticker:", self._ticker_combo)

        self._period_combo = QComboBox()
        for label, _, __ in HISTORY_OPTIONS:
            self._period_combo.addItem(label)
        self._period_combo.setCurrentIndex(3)  # 1 Year default
        form.addRow("Period:", self._period_combo)

        self._invest_spin = QDoubleSpinBox()
        self._invest_spin.setRange(100.0, 10_000_000.0)
        self._invest_spin.setValue(10_000.0)
        self._invest_spin.setSingleStep(1000.0)
        self._invest_spin.setPrefix("$")
        self._invest_spin.setDecimals(2)
        form.addRow("Initial capital:", self._invest_spin)

        v.addWidget(target_grp)

        # ── Strategy parameters ───────────────────────────────────────────
        strat_grp = QGroupBox("Strategy")
        sform = QFormLayout(strat_grp)
        sform.setContentsMargins(12, 16, 12, 12)
        sform.setSpacing(8)

        def spin(lo, hi, val, step=1):
            s = QSpinBox()
            s.setRange(lo, hi)
            s.setValue(val)
            s.setSingleStep(step)
            return s

        def dspin(lo, hi, val, step=1.0, dec=1, prefix=""):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setValue(val)
            s.setSingleStep(step)
            s.setDecimals(dec)
            if prefix:
                s.setPrefix(prefix)
            return s

        self._s_rsi_period = spin(5, 50, 14)
        self._s_rsi_ob = spin(55, 90, 70)
        self._s_rsi_os = spin(10, 45, 30)
        self._s_sma_short = spin(5, 50, 20)
        self._s_sma_medium = spin(20, 100, 50)
        self._s_min_strength = dspin(0, 100, 55.0, 5.0)
        self._s_stop_loss = dspin(0, 30, 5.0, 0.5, 1, "")
        self._s_take_profit = dspin(0, 100, 10.0, 1.0, 1, "")
        self._s_position_size = dspin(10, 100, 100.0, 10.0, 0, "")

        sform.addRow("RSI period:", self._s_rsi_period)
        sform.addRow("RSI overbought:", self._s_rsi_ob)
        sform.addRow("RSI oversold:", self._s_rsi_os)
        sform.addRow("SMA short:", self._s_sma_short)
        sform.addRow("SMA medium:", self._s_sma_medium)
        sform.addRow("Min strength %:", self._s_min_strength)
        sform.addRow("Stop loss %:", self._s_stop_loss)
        sform.addRow("Take profit %:", self._s_take_profit)
        sform.addRow("Position size %:", self._s_position_size)

        v.addWidget(strat_grp)

        # ── Run button ────────────────────────────────────────────────────
        self._run_btn = QPushButton("▶  Run Simulation")
        self._run_btn.setObjectName("success_btn")
        self._run_btn.setMinimumHeight(40)
        self._run_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._run_btn.clicked.connect(self._on_run)
        v.addWidget(self._run_btn)

        self._export_btn = QPushButton("Export Results")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        v.addWidget(self._export_btn)

        v.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Results panel ─────────────────────────────────────────────────────────

    def _build_results(self) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        # ── Metric cards row ──────────────────────────────────────────────
        self._metrics_row = QHBoxLayout()
        self._metrics_row.setSpacing(10)

        def _metric(label: str):
            frame = QFrame()
            frame.setObjectName("metric_card")
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(12, 8, 12, 8)
            fl.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #6e7681; font-size: 10px; letter-spacing: 1px;")
            val = QLabel("--")
            val.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
            val.setStyleSheet("color: #e6edf3;")
            fl.addWidget(lbl)
            fl.addWidget(val)
            return frame, val

        self._m_return, self._m_return_val = _metric("TOTAL RETURN")
        self._m_drawdown, self._m_dd_val = _metric("MAX DRAWDOWN")
        self._m_winrate, self._m_wr_val = _metric("WIN RATE")
        self._m_trades, self._m_trades_val = _metric("TOTAL TRADES")
        self._m_sharpe, self._m_sharpe_val = _metric("SHARPE RATIO")

        for frame, _ in (self._m_return, self._m_drawdown, self._m_winrate,
                         self._m_trades, self._m_sharpe):
            self._metrics_row.addWidget(frame)

        v.addLayout(self._metrics_row)

        # ── Equity curve chart ────────────────────────────────────────────
        self._equity_plot = pg.PlotWidget()
        self._equity_plot.setBackground("#0d1117")
        self._equity_plot.setMinimumHeight(260)
        for side in ("left", "bottom"):
            self._equity_plot.getAxis(side).setPen(pg.mkPen("#21262d"))
            self._equity_plot.getAxis(side).setTextPen(pg.mkPen("#6e7681"))
        for side in ("top", "right"):
            self._equity_plot.showAxis(side)
            self._equity_plot.getAxis(side).setStyle(showValues=False, tickLength=0)
            self._equity_plot.getAxis(side).setPen(pg.mkPen("#21262d"))
        self._equity_plot.setLabel("left", "Portfolio Value ($)", color="#8b949e")
        self._equity_plot.addLegend()

        self._equity_curve = self._equity_plot.plot(
            pen=pg.mkPen(color="#58a6ff", width=2), name="Portfolio"
        )
        self._baseline_line = self._equity_plot.plot(
            pen=pg.mkPen(color="#30363d", width=1, style=Qt.PenStyle.DashLine),
            name="Initial Capital",
        )
        self._fill_above = pg.FillBetweenItem(
            self._equity_curve, self._baseline_line,
            brush=pg.mkBrush(QColor(63, 185, 80, 25)),
        )
        self._fill_below = pg.FillBetweenItem(
            self._equity_curve, self._baseline_line,
            brush=pg.mkBrush(QColor(248, 81, 73, 25)),
        )
        self._equity_plot.addItem(self._fill_above)
        self._equity_plot.addItem(self._fill_below)

        v.addWidget(self._equity_plot, stretch=1)

        # ── Trade log table ───────────────────────────────────────────────
        trade_label = QLabel("TRADE LOG")
        trade_label.setStyleSheet("color: #8b949e; font-size: 10px; letter-spacing: 1.5px;")
        v.addWidget(trade_label)

        self._trade_table = QTableWidget()
        self._trade_table.setColumnCount(8)
        self._trade_table.setHorizontalHeaderLabels([
            "Entry Date", "Exit Date", "Entry $", "Exit $",
            "Shares", "P&L $", "P&L %", "Exit Reason",
        ])
        self._trade_table.setAlternatingRowColors(True)
        self._trade_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._trade_table.horizontalHeader().setStretchLastSection(True)
        self._trade_table.setMaximumHeight(220)
        self._trade_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        v.addWidget(self._trade_table)

        return container

    # ── Simulation execution ──────────────────────────────────────────────────

    def refresh_tickers(self):
        """Called when watchlist changes to update the ticker combo."""
        current = self._ticker_combo.currentText()
        self._ticker_combo.clear()
        watchlist = self._db.get_watchlist()  # would need db ref
        for entry in watchlist:
            self._ticker_combo.addItem(entry["ticker"])
        idx = self._ticker_combo.findText(current)
        if idx >= 0:
            self._ticker_combo.setCurrentIndex(idx)

    def _on_run(self):
        ticker = self._ticker_combo.currentText().strip()
        if not ticker:
            self._status_lbl.setText("Select a ticker first")
            return

        period_idx = self._period_combo.currentIndex()
        _, period, interval = HISTORY_OPTIONS[period_idx]

        self._run_btn.setEnabled(False)
        self._run_btn.setText("Running…")
        self._status_lbl.setText(f"Fetching data for {ticker}…")
        self._status_lbl.setStyleSheet("color: #58a6ff; font-size: 11px;")

        from PyQt6.QtCore import QCoreApplication
        QCoreApplication.processEvents()

        df = self._dm.get_historical(ticker, period=period, interval=interval, use_cache=False)
        if df is None or df.empty:
            self._status_lbl.setText("Failed to fetch data")
            self._status_lbl.setStyleSheet("color: #f85149; font-size: 11px;")
            self._run_btn.setEnabled(True)
            self._run_btn.setText("▶  Run Simulation")
            return

        params = StrategyParams(
            rsi_period=self._s_rsi_period.value(),
            rsi_overbought=float(self._s_rsi_ob.value()),
            rsi_oversold=float(self._s_rsi_os.value()),
            sma_short=self._s_sma_short.value(),
            sma_medium=self._s_sma_medium.value(),
            min_signal_strength=self._s_min_strength.value(),
            stop_loss_pct=self._s_stop_loss.value(),
            take_profit_pct=self._s_take_profit.value(),
            position_size_pct=self._s_position_size.value(),
        )
        engine = SimulationEngine(params)

        initial = self._invest_spin.value()

        self._status_lbl.setText("Running simulation…")

        # Run in background thread
        self._thread = QThread()
        self._worker = SimWorker(engine, ticker, df, initial, None, None)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_sim_done)
        self._worker.error.connect(self._on_sim_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_sim_done(self, result: Optional[SimulationResult]):
        self._run_btn.setEnabled(True)
        self._run_btn.setText("▶  Run Simulation")

        if result is None:
            self._status_lbl.setText("Simulation failed – insufficient data")
            self._status_lbl.setStyleSheet("color: #f85149; font-size: 11px;")
            return

        self._result = result
        self._display_results(result)

        # Save to DB
        run_id = self._db.save_simulation_run(result.to_db_dict())
        if result.trades:
            self._db.save_simulation_trades(run_id, result.trades_to_db_list())

        color = "#3fb950" if result.profitable else "#f85149"
        sign = "+" if result.profitable else ""
        self._status_lbl.setText(
            f"Done  {sign}{result.total_return_pct:.1f}%  |  {result.total_trades} trades"
        )
        self._status_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        self._export_btn.setEnabled(True)

    def _on_sim_error(self, msg: str):
        self._run_btn.setEnabled(True)
        self._run_btn.setText("▶  Run Simulation")
        self._status_lbl.setText(f"Error: {msg}")
        self._status_lbl.setStyleSheet("color: #f85149; font-size: 11px;")

    # ── Display results ───────────────────────────────────────────────────────

    def _display_results(self, r: SimulationResult):
        # Metrics
        ret_color = "#3fb950" if r.total_return_pct >= 0 else "#f85149"
        sign = "+" if r.total_return_pct >= 0 else ""
        self._m_return_val.setText(f"{sign}{r.total_return_pct:.1f}%")
        self._m_return_val.setStyleSheet(f"color: {ret_color}; font-size: 18px; font-weight: bold;")
        self._m_dd_val.setText(f"{r.max_drawdown_pct:.1f}%")
        self._m_dd_val.setStyleSheet("color: #f85149; font-size: 18px; font-weight: bold;")
        self._m_wr_val.setText(f"{r.win_rate_pct:.0f}%")
        wr_color = "#3fb950" if r.win_rate_pct >= 50 else "#f85149"
        self._m_wr_val.setStyleSheet(f"color: {wr_color}; font-size: 18px; font-weight: bold;")
        self._m_trades_val.setText(str(r.total_trades))
        self._m_trades_val.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold;")
        sharpe_color = "#3fb950" if r.sharpe_ratio >= 1.0 else "#d29922" if r.sharpe_ratio >= 0 else "#f85149"
        self._m_sharpe_val.setText(f"{r.sharpe_ratio:.2f}")
        self._m_sharpe_val.setStyleSheet(f"color: {sharpe_color}; font-size: 18px; font-weight: bold;")

        # Equity curve
        if r.equity_curve:
            values = [e["value"] for e in r.equity_curve]
            x = list(range(len(values)))
            self._equity_curve.setData(x, values)
            baseline_y = [r.initial_invest] * len(values)
            self._baseline_line.setData(x, baseline_y)
            self._equity_plot.setXRange(0, len(x) - 1, padding=0.02)
            y_min = min(min(values) * 0.98, r.initial_invest * 0.95)
            y_max = max(max(values) * 1.02, r.initial_invest * 1.05)
            self._equity_plot.setYRange(y_min, y_max, padding=0)

            # Date labels on x-axis
            dates = [e["date"] for e in r.equity_curve]
            step = max(1, len(dates) // 8)
            ticks = [(i, dates[i]) for i in range(0, len(dates), step)]
            self._equity_plot.getAxis("bottom").setTicks([ticks])

        # Trade table
        self._trade_table.setRowCount(0)
        for trade in r.trades:
            row = self._trade_table.rowCount()
            self._trade_table.insertRow(row)
            cells = [
                trade.entry_date,
                trade.exit_date,
                f"${trade.entry_price:,.2f}",
                f"${trade.exit_price:,.2f}",
                f"{trade.shares:.2f}",
                f"${trade.pnl:,.2f}",
                f"{trade.pnl_pct:+.1f}%",
                trade.exit_reason,
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 5:  # P&L $
                    item.setForeground(QColor("#3fb950" if trade.pnl >= 0 else "#f85149"))
                if col == 6:  # P&L %
                    item.setForeground(QColor("#3fb950" if trade.pnl_pct >= 0 else "#f85149"))
                self._trade_table.setItem(row, col, item)

        self._trade_table.resizeColumnsToContents()

    def _on_export(self):
        if not self._result:
            return
        from PyQt6.QtWidgets import QFileDialog
        from app.config import EXPORT_DIR
        import csv
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Simulation Results", str(EXPORT_DIR / "simulation.csv"), "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Entry Date", "Exit Date", "Entry $", "Exit $",
                             "Shares", "P&L $", "P&L %", "Exit Reason"])
            for t in self._result.trades:
                writer.writerow([
                    t.entry_date, t.exit_date, t.entry_price, t.exit_price,
                    t.shares, t.pnl, t.pnl_pct, t.exit_reason,
                ])
        self._status_lbl.setText(f"Exported to {path}")
