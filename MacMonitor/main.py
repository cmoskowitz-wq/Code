import sys
import time
import subprocess
import psutil
from collections import deque
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg

# ----------------------------
# Helper Functions
# ----------------------------

def get_ping():
    try:
        output = subprocess.check_output(
            ["ping", "-c", "1", "8.8.8.8"],
            stderr=subprocess.DEVNULL,
            universal_newlines=True
        )
        for line in output.split("\n"):
            if "time=" in line:
                return float(line.split("time=")[1].split(" ")[0])
    except:
        return None
    return None


def get_gpu_usage():
    """
    macOS has no simple API.
    Attempt lightweight powermetrics call (best effort).
    """
    try:
        output = subprocess.check_output(
            ["powermetrics", "--samplers", "gpu_power", "-n", "1"],
            stderr=subprocess.DEVNULL,
            universal_newlines=True
        )
        for line in output.split("\n"):
            if "GPU Busy" in line:
                return float(line.split(":")[1].strip().replace("%", ""))
    except:
        return None
    return None


def get_npu_usage():
    """
    Apple Neural Engine (ANE) is not publicly exposed.
    Placeholder for now.
    """
    return None


# ----------------------------
# Main App
# ----------------------------

class MoskoMeter(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mosko Meter")
        self.setGeometry(100, 100, 1000, 700)

        self.central = QtWidgets.QWidget()
        self.setCentralWidget(self.central)

        layout = QtWidgets.QVBoxLayout(self.central)

        # Dark Theme
        pg.setConfigOption("background", "#0d1117")
        pg.setConfigOption("foreground", "#c9d1d9")

        # Graph widgets
        self.cpu_plot = self.create_plot("CPU %")
        self.mem_plot = self.create_plot("Memory %")
        self.net_plot = self.create_plot("Network KB/s")
        self.latency_plot = self.create_plot("Latency (ms)")

        layout.addWidget(self.cpu_plot)
        layout.addWidget(self.mem_plot)
        layout.addWidget(self.net_plot)
        layout.addWidget(self.latency_plot)

        # Data buffers
        self.max_points = 60
        self.cpu_data = deque([0]*self.max_points, maxlen=self.max_points)
        self.mem_data = deque([0]*self.max_points, maxlen=self.max_points)
        self.net_data = deque([0]*self.max_points, maxlen=self.max_points)
        self.latency_data = deque([0]*self.max_points, maxlen=self.max_points)

        self.last_net = psutil.net_io_counters()

        # Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

    def create_plot(self, title):
        plot = pg.PlotWidget(title=title)
        plot.showGrid(x=True, y=True)
        plot.setYRange(0, 100)
        return plot

    def update_stats(self):
        # CPU
        cpu = psutil.cpu_percent()
        self.cpu_data.append(cpu)

        # Memory
        mem = psutil.virtual_memory().percent
        self.mem_data.append(mem)

        # Network
        current_net = psutil.net_io_counters()
        sent = current_net.bytes_sent - self.last_net.bytes_sent
        recv = current_net.bytes_recv - self.last_net.bytes_recv
        total_kb = (sent + recv) / 1024
        self.net_data.append(total_kb)
        self.last_net = current_net

        # Latency
        latency = get_ping()
        self.latency_data.append(latency if latency else 0)

        # GPU / NPU (optional logging)
        gpu = get_gpu_usage()
        npu = get_npu_usage()

        # Update plots
        self.refresh_plot(self.cpu_plot, self.cpu_data)
        self.refresh_plot(self.mem_plot, self.mem_data)
        self.refresh_plot(self.net_plot, self.net_data)
        self.refresh_plot(self.latency_plot, self.latency_data)

        # Window title live stats
        self.setWindowTitle(
            f"Mosko Meter | CPU {cpu:.0f}% | MEM {mem:.0f}% | "
            f"NET {total_kb:.1f} KB/s | LAT {latency if latency else '—'} ms | "
            f"GPU {gpu if gpu else '—'}% | NPU {npu if npu else '—'}"
        )

    def refresh_plot(self, plot, data):
        plot.clear()
        plot.plot(list(data), pen=pg.mkPen(width=2))


# ----------------------------
# Run App
# ----------------------------

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    window = MoskoMeter()
    window.show()

    sys.exit(app.exec())