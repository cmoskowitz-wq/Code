"""
Mosko Meter - Real-time system monitoring application for macOS.

A PyQt6/pyqtgraph-based system monitor displaying CPU, memory, network,
and latency metrics with live graphs and a status bar.
"""

import sys
import logging
import subprocess
import psutil
from collections import deque
from typing import Optional
from PyQt6 import QtWidgets, QtCore, QtGui
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
    Get GPU usage on macOS via powermetrics.

    Note: Requires elevated privileges (sudo). Returns None if unavailable.

    Returns:
        GPU busy percentage, or None if unavailable
    """
    try:
        output = subprocess.check_output(
            ["powermetrics", "--samplers", "gpu_power", "-n", "1"],
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            timeout=5
        )
        for line in output.split("\n"):
            if "GPU Busy" in line:
                try:
                    return float(line.split(":")[1].strip().replace("%", ""))
                except (ValueError, IndexError):
                    logger.debug(f"Failed to parse GPU metrics: {line}")
                    return None
    except subprocess.TimeoutExpired:
        logger.debug("powermetrics timeout")
    except FileNotFoundError:
        logger.debug("powermetrics not available (requires macOS system utility)")
    except PermissionError:
        logger.info("GPU metrics require elevated privileges (run with sudo)")
    except Exception as e:
        logger.debug(f"Failed to get GPU usage: {e}")
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
    - Network throughput (KB/s)
    - Network latency (ms)

    Also displays GPU and NPU metrics in the status bar when available.
    """

    def __init__(self):
        """Initialize the monitoring application."""
        super().__init__()

        # Window setup
        self.setWindowTitle("Mosko Meter")
        self.setGeometry(100, 100, 1200, 900)
        self.setWindowIcon(self._create_icon())

        # Central widget and layout
        self.central = QtWidgets.QWidget()
        self.setCentralWidget(self.central)
        main_layout = QtWidgets.QVBoxLayout(self.central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # Dark Theme
        pg.setConfigOption("background", DARKMODE_BG)
        pg.setConfigOption("foreground", DARKMODE_FG)

        # Create graph widgets with proper Y-axis ranges
        self.cpu_plot = self._create_plot("CPU %", y_range=(0, 100))
        self.mem_plot = self._create_plot("Memory %", y_range=(0, 100))
        self.net_plot = self._create_plot("Network KB/s", y_range=(0, 100), auto_scale=True)
        self.latency_plot = self._create_plot("Latency (ms)", y_range=(0, 100), auto_scale=True)

        # Add graphs to layout
        grid = QtWidgets.QGridLayout()
        grid.addWidget(self.cpu_plot, 0, 0)
        grid.addWidget(self.mem_plot, 0, 1)
        grid.addWidget(self.net_plot, 1, 0)
        grid.addWidget(self.latency_plot, 1, 1)
        main_layout.addLayout(grid)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_label = QtWidgets.QLabel()
        self.status_bar.addWidget(self.status_label)

        # Data buffers (store actual values, not 0 for None)
        self.max_points = MAX_DATA_POINTS
        self.cpu_data: deque = deque(maxlen=self.max_points)
        self.mem_data: deque = deque(maxlen=self.max_points)
        self.net_data: deque = deque(maxlen=self.max_points)
        self.latency_data: deque = deque(maxlen=self.max_points)

        # Network tracking
        self.last_net = psutil.net_io_counters()
        self.first_update = True

        # Y-axis tracking for auto-scaling
        self.net_max = 100
        self.latency_max = 100

        # Monitoring state
        self.is_paused = False
        self.current_cpu = 0.0
        self.current_mem = 0.0
        self.current_net = 0.0
        self.current_latency: Optional[float] = None
        self.current_gpu: Optional[float] = None
        self.current_npu: Optional[float] = None

        # Timer setup
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(UPDATE_INTERVAL)

        # Setup keyboard shortcuts
        self._setup_shortcuts()

        logger.info("Mosko Meter started")

    def _create_icon(self) -> QtGui.QIcon:
        """Create a simple application icon."""
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtGui.QColor(DARKMODE_BG))
        return QtGui.QIcon(pixmap)

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # QShortcut lives in QtGui in PyQt6 (not QtWidgets)
        QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Quit, self, self.close)
        QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Modifier.CTRL | QtCore.Qt.Key.Key_Space),
            self,
            self._toggle_pause
        )

    def _create_plot(
        self,
        title: str,
        y_range: tuple = (0, 100),
        auto_scale: bool = False
    ) -> pg.PlotWidget:
        """
        Create a styled plot widget.

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
            # CPU
            self.current_cpu = psutil.cpu_percent(interval=0.1)
            self.cpu_data.append(self.current_cpu)

            # Memory
            self.current_mem = psutil.virtual_memory().percent
            self.mem_data.append(self.current_mem)

            # Network (skip first update to avoid large spike)
            current_net = psutil.net_io_counters()
            if not self.first_update:
                sent = current_net.bytes_sent - self.last_net.bytes_sent
                recv = current_net.bytes_recv - self.last_net.bytes_recv
                self.current_net = (sent + recv) / 1024  # Convert to KB/s
                self.net_data.append(self.current_net)

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

                # Update max for auto-scaling
                if self.current_latency > self.latency_max:
                    self.latency_max = self.current_latency * 1.2
                    self.latency_plot.setYRange(0, self.latency_max)

            # GPU / NPU (optional)
            self.current_gpu = get_gpu_usage()
            self.current_npu = get_npu_usage()

            # Update plots
            self._refresh_plot(self.cpu_plot, self.cpu_data)
            self._refresh_plot(self.mem_plot, self.mem_data)
            self._refresh_plot(self.net_plot, self.net_data)
            self._refresh_plot(self.latency_plot, self.latency_data)

            # Update status bar and window title
            self._update_status()

        except Exception as e:
            logger.error(f"Error updating stats: {e}")

    def _update_status(self) -> None:
        """Update status bar and window title with current metrics."""
        cpu_str = f"CPU {self.current_cpu:.1f}%"
        mem_str = f"MEM {self.current_mem:.1f}%"
        net_str = f"NET {self.current_net:.1f} KB/s"
        lat_str = f"LAT {self.current_latency:.1f} ms" if self.current_latency else "LAT —"
        gpu_str = f"GPU {self.current_gpu:.1f}%" if self.current_gpu is not None else "GPU —"
        npu_str = f"NPU {self.current_npu:.1f}%" if self.current_npu is not None else "NPU —"
        pause_str = " [PAUSED]" if self.is_paused else ""

        # Update window title
        self.setWindowTitle(
            f"Mosko Meter | {cpu_str} | {mem_str} | {net_str} | {lat_str}{pause_str}"
        )

        # Update status bar
        self.status_label.setText(
            f"  {cpu_str}  |  {mem_str}  |  {net_str}  |  {lat_str}  |  {gpu_str}  |  {npu_str}  "
            f"[Ctrl+Space: Pause]"
        )

    def _refresh_plot(self, plot: pg.PlotWidget, data: deque) -> None:
        """
        Refresh a plot with new data.

        Args:
            plot: PlotWidget to update
            data: Deque of data points to plot
        """
        plot.clear()
        if data:
            plot.plot(list(data), pen=pg.mkPen(color="#00d4ff", width=2))

    def closeEvent(self, event):
        """Handle window close event with proper cleanup."""
        logger.info("Mosko Meter shutting down")
        self.timer.stop()
        event.accept()


# ----------------------------
# Run App
# ----------------------------

def main() -> None:
    """Launch the Mosko Meter application."""
    try:
        app = QtWidgets.QApplication(sys.argv)
        window = MoskoMeter()
        window.show()
        sys.exit(app.exec())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()