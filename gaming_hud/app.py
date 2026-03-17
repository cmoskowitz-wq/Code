"""Main HUD overlay window — assembles all widgets and connects monitors."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QFont
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from gaming_hud import __version__, styles
from gaming_hud.monitors import (
    FPSMonitor, KeyboardMonitor, MediaDetector, NetworkMonitor,
    SystemStatsMonitor,
)
from gaming_hud.widgets import (
    FPSDisplay, KeyVisualizer, MediaDisplay, NetworkDisplay,
    StatRow, make_section_label, make_separator,
)


class HUDOverlay(QWidget):
    """Frameless, translucent, always-on-top overlay window."""

    def __init__(self):
        super().__init__()
        self._drag_pos: QPoint | None = None
        self._monitors: list = []
        self._setup_window()
        self._build_ui()
        self._start_monitors()

        # Repaint timer — drives the FPS counter
        self._repaint_timer = QTimer(self)
        self._repaint_timer.timeout.connect(self.update)
        self._repaint_timer.start(16)  # ~60 fps

    # ── Window Setup ────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowTitle("Gaming HUD")
        self.setObjectName("HUDPanel")
        self.setFixedWidth(styles.HUD_WIDTH)
        self.setMinimumHeight(styles.HUD_MIN_HEIGHT)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(styles.MAIN_STYLESHEET)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # Hides from taskbar
        )

        # Position at top-right of primary screen
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.right() - styles.HUD_WIDTH - 20, geo.top() + 20)

    # ── UI Construction ─────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(
            styles.PADDING, styles.PADDING,
            styles.PADDING, styles.PADDING,
        )
        root.setSpacing(styles.SECTION_SPACING)

        # ─ Title bar ─
        title_bar = QHBoxLayout()
        title_bar.setSpacing(4)

        title = QLabel("GAMING HUD")
        title.setObjectName("title")
        tf = QFont("Segoe UI, Arial, sans-serif")
        tf.setPixelSize(styles.FONT_SIZE_TITLE)
        tf.setBold(True)
        title.setFont(tf)

        version = QLabel(f"v{__version__}")
        version.setStyleSheet(
            f"color: {styles.TEXT_DIM}; font-size: {styles.FONT_SIZE_SMALL}px;"
        )

        min_btn = QPushButton("─")
        min_btn.setObjectName("minBtn")
        min_btn.setFixedSize(24, 24)
        min_btn.setToolTip("Minimize to tray")
        min_btn.clicked.connect(self.hide)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.setToolTip("Close HUD")
        close_btn.clicked.connect(self._on_close)

        title_bar.addWidget(title)
        title_bar.addWidget(version)
        title_bar.addStretch()
        title_bar.addWidget(min_btn)
        title_bar.addWidget(close_btn)
        root.addLayout(title_bar)

        root.addWidget(make_separator())

        # ─ FPS ─
        root.addWidget(make_section_label("PERFORMANCE"))
        self._fps_display = FPSDisplay()
        root.addWidget(self._fps_display)

        root.addWidget(make_separator())

        # ─ System Stats ─
        root.addWidget(make_section_label("SYSTEM"))
        self._cpu_row = StatRow("⬡", "CPU")
        self._gpu_row = StatRow("◈", "GPU")
        self._ram_row = StatRow("▦", "RAM", unit="GB")
        root.addWidget(self._cpu_row)
        root.addWidget(self._gpu_row)
        root.addWidget(self._ram_row)

        root.addWidget(make_separator())

        # ─ Network ─
        root.addWidget(make_section_label("NETWORK"))
        self._net_display = NetworkDisplay()
        root.addWidget(self._net_display)

        root.addWidget(make_separator())

        # ─ Media ─
        self._media_display = MediaDisplay()
        root.addWidget(self._media_display)

        root.addWidget(make_separator())

        # ─ Key Visualizer ─
        root.addWidget(make_section_label("INPUT"))
        self._key_viz = KeyVisualizer()
        root.addWidget(self._key_viz)

        root.addStretch()

    # ── Monitors ────────────────────────────────────────────────────────

    def _start_monitors(self):
        # FPS
        self._fps_mon = FPSMonitor(interval_ms=styles.FPS_UPDATE_MS)
        self._fps_mon.fps_updated.connect(self._fps_display.set_fps)
        self._monitors.append(self._fps_mon)

        # System stats
        self._stats_mon = SystemStatsMonitor(
            interval_ms=styles.STATS_UPDATE_MS
        )
        self._stats_mon.stats_updated.connect(self._on_stats)
        self._monitors.append(self._stats_mon)

        # Network
        self._net_mon = NetworkMonitor(interval_ms=styles.PING_UPDATE_MS)
        self._net_mon.net_updated.connect(self._on_network)
        self._monitors.append(self._net_mon)

        # Media
        self._media_mon = MediaDetector(interval_ms=styles.MEDIA_UPDATE_MS)
        self._media_mon.media_updated.connect(self._on_media)
        self._monitors.append(self._media_mon)

        # Keyboard
        self._kb_mon = KeyboardMonitor()
        self._kb_mon.key_pressed.connect(self._key_viz.on_key_event)
        self._monitors.append(self._kb_mon)

        for m in self._monitors:
            m.start()

    def _stop_monitors(self):
        for m in self._monitors:
            m.stop()

    # ── Signal Handlers ─────────────────────────────────────────────────

    def _on_stats(self, data: dict):
        cpu = data["cpu"]
        self._cpu_row.set_value(cpu)
        self._cpu_row.set_color(styles.get_bar_color(cpu))

        gpu = data.get("gpu")
        if gpu is not None:
            self._gpu_row.set_value(gpu)
            self._gpu_row.set_color(styles.get_bar_color(gpu))
        else:
            self._gpu_row.set_value_text("N/A", 0)
            self._gpu_row.set_color(styles.TEXT_DIM)

        used = data["ram_used"]
        total = data["ram_total"]
        pct = data["ram_percent"]
        self._ram_row.set_value_text(
            f"{used:.1f} / {total:.0f} GB",
            bar_percent=pct,
            color=styles.get_bar_color(pct),
        )

    def _on_network(self, data: dict):
        self._net_display.set_data(
            data["ping"], data["upload"], data["download"]
        )

    def _on_media(self, data: dict):
        self._media_display.set_media(
            data["playing"], data["title"], data["source"]
        )

    def _on_close(self):
        self._stop_monitors()
        QApplication.quit()

    # ── Custom Painting (rounded background) ────────────────────────────

    def paintEvent(self, _event):
        # Tick FPS counter on each paint
        if hasattr(self, "_fps_mon"):
            self._fps_mon.tick()

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        rect = self.rect().adjusted(0, 0, 0, 0)
        path.addRoundedRect(
            float(rect.x()), float(rect.y()),
            float(rect.width()), float(rect.height()),
            styles.CORNER_RADIUS, styles.CORNER_RADIUS,
        )

        # Main background
        bg = QColor(styles.BG_PRIMARY)
        bg.setAlpha(230)
        p.fillPath(path, bg)

        # Subtle top border glow
        from PyQt5.QtGui import QLinearGradient
        glow = QLinearGradient(0, 0, rect.width(), 0)
        glow_color = QColor(styles.ACCENT_CYAN)
        glow_color.setAlpha(40)
        glow.setColorAt(0.0, QColor(0, 0, 0, 0))
        glow.setColorAt(0.5, glow_color)
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setClipPath(path)
        p.fillRect(0, 0, rect.width(), 2, glow)

        p.end()

    # ── Dragging ────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ── Cleanup ─────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._stop_monitors()
        super().closeEvent(event)
