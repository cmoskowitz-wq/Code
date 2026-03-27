"""
Mosko Meter - Real-time system monitoring application for macOS.

A PyQt6/pyqtgraph-based system monitor displaying CPU, memory, network,
and latency metrics with live graphs and a status bar.
"""

__version__ = "7.0.0"
__author__ = "Chris Moskowitz"
__email__ = "cmoskowitz@gmail.com"
__copyright__ = "All rights reserved 2026 copyright, Chris Moskowitz /cmoskowitz@gmail.com"

import sys
import logging
import subprocess
import os
import psutil
from collections import deque
from typing import Optional
from PySide6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MoskoMeter")

# ----------------------------
# Configuration
# ----------------------------

PING_HOST = "8.8.8.8"
UPDATE_INTERVAL = 1000  # milliseconds
MAX_DATA_POINTS = 60
DARKMODE_BG = "#0d1117"
DARKMODE_FG = "#c9d1d9"

# Modern color scheme
PRIMARY_COLOR = "#00d4ff"      # Cyan
ACCENT_COLOR = "#ff6b6b"       # Red
SUCCESS_COLOR = "#51cf66"       # Green
WARNING_COLOR = "#ffd43b"       # Yellow
SURFACE_COLOR = "#161b22"       # Darker surface
BORDER_COLOR = "#30363d"        # Border color

# ----------------------------
# Helper Functions
# ----------------------------

def get_ping(host: str = PING_HOST) -> Optional[float]:
    """
    Get network latency by pinging the specified host.

    Args:
        host: IP address or hostname to ping (default: 8.8.8.8)

    Returns:
        Latency in milliseconds, or None if ping fails
    """
    try:
        output = subprocess.check_output(
            ["ping", "-c", "1", host],
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            timeout=5
        )
        for line in output.split("\n"):
            if "time=" in line:
                try:
                    return float(line.split("time=")[1].split(" ")[0])
                except (ValueError, IndexError):
                    logger.debug(f"Failed to parse ping output: {line}")
                    return None
    except subprocess.TimeoutExpired:
        logger.debug(f"Ping timeout to {host}")
    except FileNotFoundError:
        logger.error("ping command not found")
    except PermissionError:
        logger.error("Permission denied for ping command")
    except Exception as e:
        logger.debug(f"Ping failed: {e}")
    return None


def get_gpu_usage() -> Optional[float]:
    """
    Get GPU usage on macOS via multiple methods.

    Tries powermetrics first (requires sudo), then falls back to other methods.

    Returns:
        GPU busy percentage, or None if unavailable
    """
    # Method 1: Try powermetrics with stderr redirected to stdout
    try:
        output = subprocess.run(
            ["powermetrics", "--samplers", "gpu_power", "-n", "1"],
            capture_output=True,
            universal_newlines=True,
            timeout=5
        )
        if output.returncode == 0:
            for line in output.stdout.split("\n"):
                if "GPU Busy" in line:
                    try:
                        return float(line.split(":")[1].strip().replace("%", ""))
                    except (ValueError, IndexError):
                        pass
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    # Method 2: Try ioreg (doesn't require sudo on most systems)
    try:
        output = subprocess.run(
            ["ioreg", "-r", "-w", "0", "-d", "0"],
            capture_output=True,
            universal_newlines=True,
            timeout=5
        )
        if output.returncode == 0 and "IOAccelDeviceUtilization" in output.stdout:
            import re
            match = re.search(r'IOAccelDeviceUtilization["\s:]*(\d+)', output.stdout)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    pass
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    # Method 3: Check system_profiler for GPU info (basic, not real-time)
    try:
        output = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True,
            universal_newlines=True,
            timeout=5
        )
        if output.returncode == 0 and ("M" in output.stdout or "Apple" in output.stdout):
            # Mac has integrated GPU or dedicated GPU
            # Return 0.0 as placeholder since we can't get real-time usage easily
            return 0.0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    return None


def get_npu_usage() -> Optional[float]:
    """
    Get Apple Neural Engine (ANE) usage.

    Note: ANE metrics are not publicly exposed via standard APIs.
    This is a placeholder for future implementation.

    Returns:
        NPU usage percentage, or None if unavailable
    """
    return None


# ----------------------------
# Main App
# ----------------------------

class MoskoMeter(QtWidgets.QMainWindow):
    """
    Real-time system monitoring application for macOS.

    Displays live graphs for:
    - CPU usage
    - Memory usage
    - System Load Average
    - Network throughput (KB/s)
    - Network latency (ms)
    - Disk I/O (MB/s)

    Also displays GPU and NPU metrics in the status bar when available.
    """

    def __init__(self):
        """Initialize the monitoring application."""
        super().__init__()

        # Window setup
        self.setWindowTitle("Mosko Meter v7.0")
        self.setGeometry(100, 100, 1500, 1200)
        self.setWindowIcon(self._create_icon())

        # Central widget with tabs
        self.central = QtWidgets.QWidget()
        self.setCentralWidget(self.central)
        main_layout = QtWidgets.QVBoxLayout(self.central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # Dark Theme
        pg.setConfigOption("background", DARKMODE_BG)
        pg.setConfigOption("foreground", DARKMODE_FG)

        # Apply modern stylesheet
        self._apply_stylesheet()

        # Create menu bar
        self._create_menu_bar()

        # Create tab widget
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Monitoring Dashboard
        self.monitor_tab = QtWidgets.QWidget()
        monitor_layout = QtWidgets.QVBoxLayout(self.monitor_tab)
        monitor_layout.setContentsMargins(5, 5, 5, 5)
        monitor_layout.setSpacing(3)

        # Create graph widgets with proper Y-axis ranges
        self.cpu_plot = self._create_plot("CPU %", y_range=(0, 100))
        self.mem_plot = self._create_plot("Memory %", y_range=(0, 100))
        self.load_plot = self._create_plot("System Load Avg", y_range=(0, psutil.cpu_count() * 1.5), auto_scale=True)
        self.net_plot = self._create_plot("Network KB/s", y_range=(0, 100), auto_scale=True)
        self.latency_plot = self._create_plot("Latency (ms)", y_range=(0, 100), auto_scale=True)
        self.disk_io_plot = self._create_plot("Disk I/O (MB/s)", y_range=(0, 100), auto_scale=True)

        # Add graphs to layout (3 on top, 3 on bottom)
        grid = QtWidgets.QGridLayout()
        grid.addWidget(self.cpu_plot, 0, 0)
        grid.addWidget(self.mem_plot, 0, 1)
        grid.addWidget(self.load_plot, 0, 2)
        grid.addWidget(self.net_plot, 1, 0)
        grid.addWidget(self.latency_plot, 1, 1)
        grid.addWidget(self.disk_io_plot, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        monitor_layout.addLayout(grid)
        self.tabs.addTab(self.monitor_tab, "Monitoring")

        # Tab 2: Process Manager
        self.process_tab = QtWidgets.QWidget()
        process_layout = QtWidgets.QVBoxLayout(self.process_tab)
        process_layout.setContentsMargins(5, 5, 5, 5)
        process_layout.setSpacing(5)

        # Process list table
        self.process_table = QtWidgets.QTableWidget()
        self.process_table.setColumnCount(5)
        self.process_table.setHorizontalHeaderLabels(["PID", "Process Name", "CPU %", "Memory %", "Kill"])
        self.process_table.horizontalHeader().setStretchLastSection(False)
        self.process_table.setColumnWidth(0, 80)
        self.process_table.setColumnWidth(1, 350)  # Increased width
        self.process_table.setColumnWidth(2, 100)
        self.process_table.setColumnWidth(3, 100)
        self.process_table.setColumnWidth(4, 100)  # Increased for red button
        self.process_table.setMaximumHeight(400)
        self.process_table.setAlternatingRowColors(True)
        self.process_table.setRowHeight(0, 28)
        self.process_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.process_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        # Make table fill available horizontal space
        self.process_table.horizontalHeader().setStretchLastSection(True)
        process_layout.addWidget(self.process_table)

        # Search/filter bar
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Filter:")
        self.process_filter = QtWidgets.QLineEdit()
        self.process_filter.setPlaceholderText("Search processes...")
        self.process_filter.textChanged.connect(self._filter_processes)
        self.process_filter.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.process_filter, 1)  # Stretch factor of 1
        process_layout.addLayout(search_layout)

        # Top processes display
        self.top_processes_text = QtWidgets.QTextEdit()
        self.top_processes_text.setReadOnly(True)
        self.top_processes_text.setMaximumHeight(400)
        self.top_processes_text.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        process_layout.addWidget(QtWidgets.QLabel("Top 10 Processes by Memory:"))
        process_layout.addWidget(self.top_processes_text)

        self.tabs.addTab(self.process_tab, "Processes")

        # Tab 3: System Information & Disk
        self.system_tab = QtWidgets.QWidget()
        system_layout = QtWidgets.QVBoxLayout(self.system_tab)
        system_layout.setContentsMargins(5, 5, 5, 5)
        system_layout.setSpacing(5)

        # System info display
        self.system_info_text = QtWidgets.QTextEdit()
        self.system_info_text.setReadOnly(True)
        self.system_info_text.setMaximumHeight(250)
        self.system_info_text.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        system_layout.addWidget(QtWidgets.QLabel("System Information:"))
        system_layout.addWidget(self.system_info_text)

        # Disk usage
        self.disk_table = QtWidgets.QTableWidget()
        self.disk_table.setColumnCount(4)
        self.disk_table.setHorizontalHeaderLabels(["Mount Point", "Total (GB)", "Used (GB)", "Used %"])
        self.disk_table.horizontalHeader().setStretchLastSection(False)
        self.disk_table.setColumnWidth(0, 250)  # Increased
        self.disk_table.setColumnWidth(1, 120)
        self.disk_table.setColumnWidth(2, 120)
        self.disk_table.setColumnWidth(3, 100)
        self.disk_table.setAlternatingRowColors(True)
        self.disk_table.setMaximumHeight(300)
        self.disk_table.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        # Make disk table fill horizontal space
        self.disk_table.horizontalHeader().setStretchLastSection(True)
        system_layout.addWidget(QtWidgets.QLabel("Disk Usage:"))
        system_layout.addWidget(self.disk_table)

        # Settings section
        settings_layout = QtWidgets.QHBoxLayout()
        settings_layout.addWidget(QtWidgets.QLabel("CPU Alert Threshold (%)"))
        self.cpu_threshold = QtWidgets.QSpinBox()
        self.cpu_threshold.setMinimum(10)
        self.cpu_threshold.setMaximum(100)
        self.cpu_threshold.setValue(80)
        settings_layout.addWidget(self.cpu_threshold)

        settings_layout.addWidget(QtWidgets.QLabel("Memory Alert Threshold (%)"))
        self.mem_threshold = QtWidgets.QSpinBox()
        self.mem_threshold.setMinimum(10)
        self.mem_threshold.setMaximum(100)
        self.mem_threshold.setValue(85)
        settings_layout.addWidget(self.mem_threshold)

        export_btn = QtWidgets.QPushButton("Export Data")
        export_btn.clicked.connect(self._export_data)
        settings_layout.addWidget(export_btn)
        settings_layout.addStretch()

        system_layout.addLayout(settings_layout)
        self.tabs.addTab(self.system_tab, "System")

        # Status bar
        self.status_bar = self.statusBar()
        self.status_label = QtWidgets.QLabel()
        self.status_bar.addWidget(self.status_label)

        # Data buffers (store actual values, not 0 for None)
        self.max_points = MAX_DATA_POINTS
        self.cpu_data: deque = deque(maxlen=self.max_points)
        self.mem_data: deque = deque(maxlen=self.max_points)
        self.load_data: deque = deque(maxlen=self.max_points)
        self.net_data: deque = deque(maxlen=self.max_points)
        self.latency_data: deque = deque(maxlen=self.max_points)
        self.disk_read_data: deque = deque(maxlen=self.max_points)
        self.disk_write_data: deque = deque(maxlen=self.max_points)

        # Network/Disk tracking
        self.last_net = psutil.net_io_counters()
        self.last_disk_io = psutil.disk_io_counters()
        self.first_update = True

        # Y-axis tracking for auto-scaling
        self.net_max = 100
        self.latency_max = 100
        self.disk_max = 100

        # Monitoring state
        self.is_paused = False
        self.current_cpu = 0.0
        self.current_mem = 0.0
        self.current_load = 0.0
        self.current_net = 0.0
        self.current_latency: Optional[float] = None
        self.current_disk_read = 0.0
        self.current_disk_write = 0.0
        self.current_npu: Optional[float] = None

        # Stats tracking for each metric
        self.cpu_stats = {"min": 0, "max": 100, "avg": 0}
        self.mem_stats = {"min": 0, "max": 100, "avg": 0}
        self.load_stats = {"min": 0, "max": 100, "avg": 0}
        self.net_stats = {"min": 0, "max": 100, "avg": 0}
        self.latency_stats = {"min": 0, "max": 100, "avg": 0}
        self.disk_read_stats = {"min": 0, "max": 100, "avg": 0}
        self.disk_write_stats = {"min": 0, "max": 100, "avg": 0}

        # Process tracking
        self.process_cache = {}
        self.all_processes = []

        # Timer setup
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(UPDATE_INTERVAL)

        # Process update timer (less frequent - every 2 seconds)
        self.process_timer = QtCore.QTimer()
        self.process_timer.timeout.connect(self._update_processes)
        self.process_timer.start(2000)

        # System info update timer (every 5 seconds)
        self.system_timer = QtCore.QTimer()
        self.system_timer.timeout.connect(self._update_system_info)
        self.system_timer.start(5000)

        # Disk info update timer (every 3 seconds)
        self.disk_timer = QtCore.QTimer()
        self.disk_timer.timeout.connect(self._update_disk_info)
        self.disk_timer.start(3000)

        # Setup keyboard shortcuts
        self._setup_shortcuts()

        # Initial loads
        self._update_processes()
        self._update_system_info()
        self._update_disk_info()

        logger.info("Mosko Meter v7.0 started successfully")

    def _create_icon(self) -> QtGui.QIcon:
        """Create a simple application icon."""
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtGui.QColor(DARKMODE_BG))
        return QtGui.QIcon(pixmap)

    def _apply_stylesheet(self) -> None:
        """Apply modern dark theme stylesheet."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {DARKMODE_BG};
                color: {DARKMODE_FG};
            }}
            
            QTabWidget::pane {{
                border: 1px solid {BORDER_COLOR};
                background-color: {SURFACE_COLOR};
            }}
            
            QTabBar::tab {{
                background-color: {SURFACE_COLOR};
                color: {DARKMODE_FG};
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid {BORDER_COLOR};
                border-bottom: none;
            }}
            
            QTabBar::tab:selected {{
                background-color: {PRIMARY_COLOR};
                color: #000000;
                font-weight: bold;
            }}
            
            QTabBar::tab:hover {{
                background-color: {BORDER_COLOR};
            }}
            
            QTableWidget {{
                background-color: {SURFACE_COLOR};
                color: {DARKMODE_FG};
                gridline-color: {BORDER_COLOR};
                selection-background-color: {PRIMARY_COLOR};
                selection-color: #000000;
                alternate-background-color: {DARKMODE_BG};
            }}
            
            QTableWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {BORDER_COLOR};
            }}
            
            QTableWidget::item:selected {{
                background-color: {PRIMARY_COLOR};
                color: #000000;
            }}
            
            QHeaderView::section {{
                background-color: {DARKMODE_BG};
                color: {DARKMODE_FG};
                padding: 8px;
                border: 1px solid {BORDER_COLOR};
                font-weight: bold;
            }}
            
            QTextEdit {{
                background-color: {SURFACE_COLOR};
                color: {DARKMODE_FG};
                border: 1px solid {BORDER_COLOR};
                padding: 4px;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
            }}
            
            QLineEdit {{
                background-color: {SURFACE_COLOR};
                color: {DARKMODE_FG};
                border: 1px solid {BORDER_COLOR};
                padding: 4px;
                selection-background-color: {PRIMARY_COLOR};
            }}
            
            QLineEdit:focus {{
                border-color: {PRIMARY_COLOR};
            }}
            
            QPushButton {{
                background-color: {SURFACE_COLOR};
                color: {DARKMODE_FG};
                border: 1px solid {BORDER_COLOR};
                padding: 6px 12px;
                border-radius: 4px;
            }}
            
            QPushButton:hover {{
                background-color: {BORDER_COLOR};
                border-color: {PRIMARY_COLOR};
            }}
            
            QPushButton:pressed {{
                background-color: {PRIMARY_COLOR};
                color: #000000;
            }}
            
            QPushButton:disabled {{
                background-color: {DARKMODE_BG};
                color: #666666;
                border-color: #444444;
            }}
            
            QSpinBox {{
                background-color: {SURFACE_COLOR};
                color: {DARKMODE_FG};
                border: 1px solid {BORDER_COLOR};
                padding: 2px;
                min-width: 60px;
            }}
            
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {BORDER_COLOR};
                border: none;
                width: 16px;
            }}
            
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {PRIMARY_COLOR};
            }}
            
            QLabel {{
                color: {DARKMODE_FG};
                font-weight: bold;
            }}
            
            QMenuBar {{
                background-color: {DARKMODE_BG};
                color: {DARKMODE_FG};
                border-bottom: 1px solid {BORDER_COLOR};
            }}
            
            QMenuBar::item {{
                background-color: transparent;
                padding: 4px 8px;
                margin: 0px 2px;
            }}
            
            QMenuBar::item:selected {{
                background-color: {PRIMARY_COLOR};
                color: #000000;
            }}
            
            QMenu {{
                background-color: {SURFACE_COLOR};
                color: {DARKMODE_FG};
                border: 1px solid {BORDER_COLOR};
            }}
            
            QMenu::item {{
                padding: 4px 20px;
            }}
            
            QMenu::item:selected {{
                background-color: {PRIMARY_COLOR};
                color: #000000;
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {BORDER_COLOR};
                margin: 2px 0px;
            }}
            
            QStatusBar {{
                background-color: {DARKMODE_BG};
                color: {DARKMODE_FG};
                border-top: 1px solid {BORDER_COLOR};
            }}
            
            QStatusBar QLabel {{
                color: {DARKMODE_FG};
                font-family: 'Courier New', monospace;
                font-size: 9pt;
            }}
        """)

    def _create_menu_bar(self) -> None:
        """Create application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        export_action = file_menu.addAction("Export Data as CSV")
        export_action.triggered.connect(self._export_data)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # View menu
        view_menu = menubar.addMenu("View")
        refresh_action = view_menu.addAction("Refresh Now")
        refresh_action.triggered.connect(self._update_stats)

        # Help menu
        help_menu = menubar.addMenu("Help")
        shortcuts_action = help_menu.addAction("Keyboard Shortcuts")
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addSeparator()
        about_action = help_menu.addAction("About Mosko Meter")
        about_action.triggered.connect(self._show_about)

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # QShortcut lives in QtGui in PyQt6 (not QtWidgets)
        QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Quit, self, self.close)
        QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Modifier.CTRL | QtCore.Qt.Key.Key_Space),
            self,
            self._toggle_pause
        )
        QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Modifier.CTRL | QtCore.Qt.Key.Key_E),
            self,
            self._export_data
        )

    def _create_plot(
        self,
        title: str,
        y_range: tuple = (0, 100),
        auto_scale: bool = False
    ) -> pg.PlotWidget:
        """
        Create a styled plot widget with enhanced visualization.

        Args:
            title: Plot title
            y_range: Initial (min, max) for Y-axis
            auto_scale: Whether to auto-scale Y-axis based on data

        Returns:
            Configured PlotWidget
        """
        plot = pg.PlotWidget(title=title)
        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.setYRange(y_range[0], y_range[1])
        plot.setLabel("bottom", "Time (s)")
        plot.setLabel("left", title.split()[0])
        plot.auto_scale = auto_scale
        
        # Create plot line items (persistent for smooth updates)
        plot.line_item = plot.plot(
            pen=pg.mkPen(color="#ff0000", width=2.5),
            name="Data"
        )
        
        # Create average reference line
        plot.avg_ref_line = plot.plot(
            pen=pg.mkPen(color="#666666", width=1, style=QtCore.Qt.PenStyle.DashLine),
            name="Average"
        )
        
        # Create scatter point for current value
        plot.scatter = pg.ScatterPlotItem()
        plot.addItem(plot.scatter)
        
        # Create text item for centered value display
        plot.value_text = pg.TextItem(text="", color="#00ff00", anchor=(0.5, 0.5))
        plot.value_text.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Weight.Bold))
        plot.addItem(plot.value_text)
        
        return plot

    def _toggle_pause(self) -> None:
        """Toggle monitoring pause/resume (Ctrl+Space)."""
        self.is_paused = not self.is_paused
        status = "PAUSED" if self.is_paused else "MONITORING"
        logger.info(f"Monitoring {status}")

    def _update_stats(self) -> None:
        """Update system statistics and refresh plots."""
        if self.is_paused:
            return

        try:
            # CPU (interval=None for non-blocking)
            self.current_cpu = psutil.cpu_percent(interval=None)
            self.cpu_data.append(self.current_cpu)
            self._update_metric_stats(self.cpu_data, self.cpu_stats)

            # Memory
            self.current_mem = psutil.virtual_memory().percent
            self.mem_data.append(self.current_mem)
            self._update_metric_stats(self.mem_data, self.mem_stats)

            # System Load Average (1-minute load average)
            load_avg = os.getloadavg()[0]
            self.current_load = load_avg
            self.load_data.append(self.current_load)
            self._update_metric_stats(self.load_data, self.load_stats)

            # Network (skip first update to avoid large spike)
            current_net = psutil.net_io_counters()
            if not self.first_update:
                sent = current_net.bytes_sent - self.last_net.bytes_sent
                recv = current_net.bytes_recv - self.last_net.bytes_recv
                self.current_net = (sent + recv) / 1024  # Convert to KB/s
                self.net_data.append(self.current_net)
                self._update_metric_stats(self.net_data, self.net_stats)

                # Update max for auto-scaling
                if self.current_net > self.net_max:
                    self.net_max = self.current_net * 1.2
                    self.net_plot.setYRange(0, self.net_max)
            else:
                self.first_update = False

            self.last_net = current_net

            # Latency (only add valid values)
            self.current_latency = get_ping()
            if self.current_latency is not None:
                self.latency_data.append(self.current_latency)
                self._update_metric_stats(self.latency_data, self.latency_stats)

                # Update max for auto-scaling
                if self.current_latency > self.latency_max:
                    self.latency_max = self.current_latency * 1.2
                    self.latency_plot.setYRange(0, self.latency_max)

            # Disk I/O (skip first update to avoid large spike)
            current_disk_io = psutil.disk_io_counters()
            if not self.first_update:
                read_bytes = current_disk_io.read_bytes - self.last_disk_io.read_bytes
                write_bytes = current_disk_io.write_bytes - self.last_disk_io.write_bytes
                self.current_disk_read = read_bytes / (1024 * 1024)  # Convert to MB/s
                self.current_disk_write = write_bytes / (1024 * 1024)  # Convert to MB/s
                self.disk_read_data.append(self.current_disk_read)
                self.disk_write_data.append(self.current_disk_write)
                self._update_metric_stats(self.disk_read_data, self.disk_read_stats)
                self._update_metric_stats(self.disk_write_data, self.disk_write_stats)

                # Update max for auto-scaling
                max_disk = max(self.current_disk_read, self.current_disk_write)
                if max_disk > self.disk_max:
                    self.disk_max = max_disk * 1.2
                    self.disk_io_plot.setYRange(0, self.disk_max)

            self.last_disk_io = current_disk_io

            # GPU / NPU (optional)
            self.current_npu = get_npu_usage()

            # Update plots only if they have data
            if self.cpu_data:
                self._refresh_plot(self.cpu_plot, self.cpu_data, self.cpu_stats)
            if self.mem_data:
                self._refresh_plot(self.mem_plot, self.mem_data, self.mem_stats)
            if self.load_data:
                self._refresh_plot(self.load_plot, self.load_data, self.load_stats)
            if self.net_data:
                self._refresh_plot(self.net_plot, self.net_data, self.net_stats)
            if self.latency_data:
                self._refresh_plot(self.latency_plot, self.latency_data, self.latency_stats)
            if self.disk_read_data:
                self._refresh_disk_plot()

            # Update status bar and window title
            self._update_status()

        except Exception as e:
            logger.error(f"Error updating stats: {e}")

    def _update_metric_stats(self, data: deque, stats: dict) -> None:
        """
        Update min/max/avg stats for a metric.

        Args:
            data: Deque of data points
            stats: Dictionary with 'min', 'max', 'avg' keys
        """
        if not data:
            return
        
        stats['min'] = min(data)
        stats['max'] = max(data)
        stats['avg'] = sum(data) / len(data)

    def _refresh_plot(self, plot: pg.PlotWidget, data: deque, stats: dict) -> None:
        """
        Refresh a plot with smooth data updates and centered value display.

        Args:
            plot: PlotWidget to update
            data: Deque of data points to plot
            stats: Dictionary containing min, max, avg values
        """
        if not data or len(data) == 0:
            return
        
        try:
            data_list = list(data)
            x_values = list(range(len(data_list)))
            current_value = data_list[-1]
            
            # Update main red line smoothly with setData
            plot.line_item.setData(x_values, data_list)
            
            # Calculate and update moving average (5-point)
            window_size = min(5, len(data_list))
            if window_size > 1:
                moving_avg = []
                for i in range(len(data_list)):
                    start = max(0, i - window_size + 1)
                    avg = sum(data_list[start:i+1]) / (i - start + 1)
                    moving_avg.append(avg)
                plot.avg_line_item.setData(x_values, moving_avg)
            
            # Update average reference line (horizontal)
            avg_val = stats['avg'] if stats['avg'] > 0 else 50
            plot.avg_ref_line.setData([0, max(1, len(data_list) - 1)], [avg_val, avg_val])
            
            # Update scatter point for current value
            plot.scatter.clear()
            plot.scatter.addPoints(
                x=[len(data_list) - 1],
                y=[current_value],
                size=10,
                brush=pg.mkBrush("#00ff00"),
                pen=pg.mkPen("#ffffff", width=2)
            )
            
            # Determine text color based on value
            max_val = max(stats['max'], current_value, 1)
            warn_threshold = max_val * 0.75
            text_color = "#ff6600" if current_value > warn_threshold else "#00ff00"
            plot.value_text.setColor(pg.mkColor(text_color))
            
            # Update centered text with current value
            text_str = f"{current_value:.1f}"
            plot.value_text.setText(text_str)
            
            # Position text prominently at the top center of the plot
            center_x = max(0, (len(data_list) - 1) / 2)
            # Position at 80% of max value to be clearly visible
            text_y = max_val * 0.8
            plot.value_text.setPos(center_x, text_y)
            
        except Exception as e:
            # Silently handle errors to maintain smooth operation
            pass

    def _refresh_disk_plot(self) -> None:
        """Refresh disk I/O plot with separate read and write lines."""
        if not self.disk_read_data or not self.disk_write_data:
            return
        
        try:
            read_list = list(self.disk_read_data)
            write_list = list(self.disk_write_data)
            x_values = list(range(len(read_list)))
            
            current_read = read_list[-1]
            current_write = write_list[-1]
            
            # Update read line (red)
            if not hasattr(self.disk_io_plot, 'read_line_item'):
                self.disk_io_plot.read_line_item = self.disk_io_plot.plot(
                    pen=pg.mkPen(color="#ff0000", width=2.5),
                    name="Read Speed"
                )
            self.disk_io_plot.read_line_item.setData(x_values, read_list)
            
            # Update write line (yellow/orange)
            if not hasattr(self.disk_io_plot, 'write_line_item'):
                self.disk_io_plot.write_line_item = self.disk_io_plot.plot(
                    pen=pg.mkPen(color="#ffd43b", width=2.5),
                    name="Write Speed"
                )
            self.disk_io_plot.write_line_item.setData(x_values, write_list)
            
            # Calculate moving average for both
            window_size = min(5, len(read_list))
            if window_size > 1:
                read_avg = []
                write_avg = []
                for i in range(len(read_list)):
                    start = max(0, i - window_size + 1)
                    read_avg.append(sum(read_list[start:i+1]) / (i - start + 1))
                    write_avg.append(sum(write_list[start:i+1]) / (i - start + 1))
                
                if not hasattr(self.disk_io_plot, 'read_avg_line'):
                    self.disk_io_plot.read_avg_line = self.disk_io_plot.plot(
                        pen=pg.mkPen(color="#ff6666", width=1.5, style=QtCore.Qt.PenStyle.DashLine),
                        name="Read Trend"
                    )
                self.disk_io_plot.read_avg_line.setData(x_values, read_avg)
                
                if not hasattr(self.disk_io_plot, 'write_avg_line'):
                    self.disk_io_plot.write_avg_line = self.disk_io_plot.plot(
                        pen=pg.mkPen(color="#ffeb99", width=1.5, style=QtCore.Qt.PenStyle.DashLine),
                        name="Write Trend"
                    )
                self.disk_io_plot.write_avg_line.setData(x_values, write_avg)
            
            # Update scatter points for current values
            if not hasattr(self.disk_io_plot, 'scatter'):
                self.disk_io_plot.scatter = pg.ScatterPlotItem()
                self.disk_io_plot.addItem(self.disk_io_plot.scatter)
            
            self.disk_io_plot.scatter.clear()
            self.disk_io_plot.scatter.addPoints(
                x=[len(read_list) - 1, len(read_list) - 1],
                y=[current_read, current_write],
                size=10,
                brush=pg.mkBrush("#00ff00"),
                pen=pg.mkPen("#ffffff", width=2)
            )
            
            # Update text display with both values
            max_val = max(self.disk_read_stats['max'], self.disk_write_stats['max'], 1)
            text_str = f"R: {current_read:.1f}\nW: {current_write:.1f}"
            
            if not hasattr(self.disk_io_plot, 'value_text'):
                self.disk_io_plot.value_text = pg.TextItem(text=text_str, color="#00ff00")
                self.disk_io_plot.value_text.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Weight.Bold))
                self.disk_io_plot.addItem(self.disk_io_plot.value_text)
            
            self.disk_io_plot.value_text.setText(text_str)
            center_x = max(0, (len(read_list) - 1) / 2)
            # Position at 75% of max value for visibility
            text_y = max_val * 0.75
            self.disk_io_plot.value_text.setPos(center_x, text_y)
            
        except Exception as e:
            # Silently handle errors to maintain smooth operation
            pass

    def _update_processes(self) -> None:
        """Update process list and display (called every 2 seconds)."""
        try:
            # Get all processes with their resource usage
            self.all_processes = []
            
            for proc in psutil.process_iter():
                try:
                    # Get process info with timeout
                    with proc.oneshot():
                        pinfo = {
                            'pid': proc.pid,
                            'name': proc.name(),
                            'cpu_percent': proc.cpu_percent(interval=None) or 0,
                            'memory_percent': proc.memory_percent() or 0
                        }
                        self.all_processes.append(pinfo)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Update the display
            self._populate_process_table()
            self._update_top_processes()
            
        except Exception as e:
            logger.error(f"Error updating processes: {e}")

    def _populate_process_table(self) -> None:
        """Populate the process table with current data."""
        try:
            # Filter processes based on search
            filter_text = self.process_filter.text().lower()
            filtered_processes = [
                p for p in self.all_processes
                if filter_text in p['name'].lower() or filter_text in str(p['pid'])
            ]
            
            # Sort by memory usage (highest first)
            filtered_processes.sort(key=lambda x: x['memory_percent'], reverse=True)
            
            self.process_table.setRowCount(len(filtered_processes))
            
            for row, proc in enumerate(filtered_processes):
                # PID
                pid_item = QtWidgets.QTableWidgetItem(str(proc['pid']))
                pid_item.setData(QtCore.Qt.ItemDataRole.UserRole, proc['pid'])
                self.process_table.setItem(row, 0, pid_item)
                
                # Name
                name_item = QtWidgets.QTableWidgetItem(proc['name'])
                name_item.setData(QtCore.Qt.ItemDataRole.UserRole, proc['pid'])
                self.process_table.setItem(row, 1, name_item)
                
                # CPU %
                cpu_item = QtWidgets.QTableWidgetItem(f"{proc['cpu_percent']:.1f}")
                cpu_item.setData(QtCore.Qt.ItemDataRole.UserRole, proc['pid'])
                self.process_table.setItem(row, 2, cpu_item)
                
                # Memory %
                mem_item = QtWidgets.QTableWidgetItem(f"{proc['memory_percent']:.1f}")
                mem_item.setData(QtCore.Qt.ItemDataRole.UserRole, proc['pid'])
                self.process_table.setItem(row, 3, mem_item)
                
                # Kill button
                kill_btn = QtWidgets.QPushButton("Kill")
                kill_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ff4444;
                        color: white;
                        border: 1px solid #cc0000;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #ff6666;
                        border-color: #aa0000;
                    }
                    QPushButton:pressed {
                        background-color: #cc0000;
                    }
                """)
                kill_btn.clicked.connect(lambda checked, pid=proc['pid']: self._kill_process(pid))
                self.process_table.setCellWidget(row, 4, kill_btn)
                
        except Exception as e:
            logger.error(f"Error populating process table: {e}")

    def _filter_processes(self) -> None:
        """Filter processes based on search text."""
        self._populate_process_table()

    def _kill_process(self, pid: int) -> None:
        """Kill a process by PID with confirmation."""
        try:
            # Get process name for confirmation
            proc_name = "Unknown"
            for proc in self.all_processes:
                if proc['pid'] == pid:
                    proc_name = proc['name']
                    break
            
            reply = QtWidgets.QMessageBox.question(
                self,
                "Confirm Process Termination",
                f"Are you sure you want to kill process '{proc_name}' (PID: {pid})?\n\n"
                "This action cannot be undone.",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                import signal
                os.kill(pid, signal.SIGTERM)
                QtWidgets.QMessageBox.information(
                    self,
                    "Process Terminated",
                    f"Process '{proc_name}' (PID: {pid}) has been terminated."
                )
                # Refresh process list
                self._update_processes()
                
        except ProcessLookupError:
            QtWidgets.QMessageBox.warning(
                self,
                "Process Not Found",
                f"Process with PID {pid} no longer exists."
            )
        except PermissionError:
            QtWidgets.QMessageBox.critical(
                self,
                "Permission Denied",
                f"Cannot kill process '{proc_name}' (PID: {pid}).\n\n"
                "You may need elevated privileges to kill system processes."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to kill process: {e}"
            )

    def _update_top_processes(self) -> None:
        """Update the top 10 processes display."""
        try:
            # Sort by memory usage
            sorted_procs = sorted(
                self.all_processes,
                key=lambda x: x['memory_percent'],
                reverse=True
            )
            
            text = ""
            for i, proc in enumerate(sorted_procs[:10], 1):
                name = proc['name'][:39]  # Truncate long names
                pid = proc['pid']
                mem = proc['memory_percent']
                cpu = proc['cpu_percent']
                text += f"{i:2d}. {name:<40} PID: {pid:<8} MEM: {mem:6.2f}%  CPU: {cpu:6.1f}%\n"
            
            self.top_processes_text.setText(text)
            
        except Exception as e:
            logger.error(f"Error updating top processes: {e}")

    def _update_system_info(self) -> None:
        """Update system information display."""
        try:
            import platform
            uname = platform.uname()
            
            # Calculate uptime
            import time
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            uptime_hours = uptime_seconds / 3600
            uptime_days = uptime_hours / 24
            
            # Memory info
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            info_text = f"""SYSTEM INFORMATION
═══════════════════════════════════════════════════════════

OS:                {uname.system} {uname.release}
Hostname:          {uname.node}
Architecture:      {uname.machine}
Processor:         {uname.processor}

CPU Cores:         {psutil.cpu_count(logical=False)} Physical / {psutil.cpu_count()} Logical
Memory:            {mem.total / (1024**3):.1f} GB
Memory Available:  {mem.available / (1024**3):.1f} GB
Swap Memory:       {swap.total / (1024**3):.1f} GB

System Uptime:     {uptime_days:.1f} days ({uptime_hours:.1f} hours)

Python Version:    {platform.python_version()}"""
            self.system_info_text.setText(info_text)
        except Exception as e:
            logger.error(f"Error updating system info: {e}")

    def _update_disk_info(self) -> None:
        """Update disk usage information."""
        try:
            self.disk_table.setRowCount(0)
            
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    row = self.disk_table.rowCount()
                    self.disk_table.insertRow(row)
                    
                    total_gb = usage.total / (1024**3)
                    used_gb = usage.used / (1024**3)
                    percent = usage.percent
                    
                    self.disk_table.setItem(row, 0, QtWidgets.QTableWidgetItem(partition.mountpoint))
                    self.disk_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{total_gb:.1f}"))
                    self.disk_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{used_gb:.1f}"))
                    self.disk_table.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{percent:.1f}%"))
                except (PermissionError, OSError):
                    pass
        except Exception as e:
            logger.error(f"Error updating disk info: {e}")

    def _export_data(self) -> None:
        """Export performance metrics as CSV."""
        try:
            from datetime import datetime
            filename = f"mosko_meter_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = QtWidgets.QFileDialog.getSaveFileName(self, "Export Data", filename, "CSV Files (*.csv)")[0]
            
            if not filepath:
                return
            
            with open(filepath, 'w') as f:
                f.write("Mosko Meter Performance Export\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # CPU data
                f.write("CPU Data\n")
                f.write("Index,CPU %\n")
                for i, val in enumerate(self.cpu_data):
                    f.write(f"{i},{val:.1f}\n")
                
                f.write("\nMemory Data\n")
                f.write("Index,Memory %\n")
                for i, val in enumerate(self.mem_data):
                    f.write(f"{i},{val:.1f}\n")
                
                f.write("\nLoad Average Data\n")
                f.write("Index,Load Average\n")
                for i, val in enumerate(self.load_data):
                    f.write(f"{i},{val:.2f}\n")
                
                f.write("\nNetwork Data\n")
                f.write("Index,Network KB/s\n")
                for i, val in enumerate(self.net_data):
                    f.write(f"{i},{val:.1f}\n")
                
                f.write("\nLatency Data\n")
                f.write("Index,Latency ms\n")
                for i, val in enumerate(self.latency_data):
                    f.write(f"{i},{val:.1f}\n")
                
                f.write("\nDisk Read Data\n")
                f.write("Index,Disk Read MB/s\n")
                for i, val in enumerate(self.disk_read_data):
                    f.write(f"{i},{val:.1f}\n")
                
                f.write("\nDisk Write Data\n")
                f.write("Index,Disk Write MB/s\n")
                for i, val in enumerate(self.disk_write_data):
                    f.write(f"{i},{val:.1f}\n")
            
            QtWidgets.QMessageBox.information(self, "Export Successful", f"Data exported to:\n{filepath}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export Failed", f"Error exporting data: {e}")

    def _show_shortcuts(self) -> None:
        """Show keyboard shortcuts dialog."""
        shortcuts_text = """KEYBOARD SHORTCUTS
═══════════════════════════════════════════════════════

Ctrl+Space    →    Pause/Resume monitoring
Ctrl+Q        →    Exit application
Ctrl+E        →    Export data as CSV

Tab Navigation  →  Switch between tabs using keyboard
Click to Kill    →  Right-click process to terminate"""
        
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Keyboard Shortcuts")
        dialog.setGeometry(200, 200, 500, 300)
        
        layout = QtWidgets.QVBoxLayout()
        text = QtWidgets.QTextEdit()
        text.setText(shortcuts_text)
        text.setReadOnly(True)
        layout.addWidget(text)
        
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()

    def _show_about(self) -> None:
        """Show about dialog."""
        about_text = f"""╔════════════════════════════════════════════════════════════════╗
║                     MOSKO METER v{__version__}                           ║
║                  Professional System Monitor                   ║
╚════════════════════════════════════════════════════════════════╝

FEATURES:
─────────────────────────────────────────────────────────────────
✓ Real-time CPU, Memory, Network, Latency monitoring
✓ Advanced Process Manager with process termination capability
✓ System Information and Disk Usage tracking
✓ Performance Metrics with Min/Max/Average statistics
✓ Customizable Alert Thresholds
✓ Data Export to CSV format
✓ Modern Dark Theme Interface
✓ Smooth, responsive charts with animations
✓ Network Speed Analysis
✓ Memory & CPU Trend Analysis
✓ Multiple monitoring tabs
✓ Keyboard shortcuts support

ABOUT:
─────────────────────────────────────────────────────────────────
Mosko Meter is a professional-grade system monitoring tool
designed for macOS systems. It provides real-time insights into
system performance with an intuitive, modern interface.

{__copyright__}

Built with PyQt6 and pyqtgraph for high-performance visualization.

SYSTEM REQUIREMENTS:
─────────────────────────────────────────────────────────────────
• macOS 10.15 or later
• Python 3.8+
• PyQt6
• psutil
• pyqtgraph

SUPPORT:
─────────────────────────────────────────────────────────────────
For questions, support, or feature requests:
Email: {__email__}"""
        
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"About Mosko Meter v{__version__}")
        dialog.setGeometry(150, 150, 750, 650)
        
        layout = QtWidgets.QVBoxLayout()
        text = QtWidgets.QTextEdit()
        text.setText(about_text)
        text.setReadOnly(True)
        text.setFont(QtGui.QFont("Courier", 9))
        layout.addWidget(text)
        
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()

    def closeEvent(self, event):
        """Handle window close event with proper cleanup."""
        logger.info("Mosko Meter shutting down")
        self.timer.stop()
        self.process_timer.stop()
        self.system_timer.stop()
        self.disk_timer.stop()
        event.accept()


# ----------------------------
# Run App
# ----------------------------

def main() -> None:
    """Launch the Mosko Meter application."""
    try:
        # Check Python version
        if sys.version_info < (3, 8):
            print(f"Error: Mosko Meter requires Python 3.8 or higher. Current version: {sys.version}")
            sys.exit(1)
        
        # Check for required modules
        required_modules = ['PyQt6', 'pyqtgraph', 'psutil']
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            print(f"Error: Missing required modules: {', '.join(missing_modules)}")
            print("Please install requirements: pip install -r requirements.txt")
            sys.exit(1)
        
        # Check if running on macOS
        if sys.platform != 'darwin':
            print("Warning: Mosko Meter is designed for macOS. Some features may not work on other platforms.")
        
        print(f"Mosko Meter v{__version__} - Starting up...")
        
        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName("Mosko Meter")
        app.setApplicationVersion(__version__)
        app.setOrganizationName("Chris Moskowitz")
        
        window = MoskoMeter()
        window.show()
        
        print("Mosko Meter started successfully!")
        sys.exit(app.exec())
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("\nMosko Meter shutdown by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error starting Mosko Meter: {e}")
        print("Check the log file for more details.")
        sys.exit(1)


if __name__ == "__main__":
    main()