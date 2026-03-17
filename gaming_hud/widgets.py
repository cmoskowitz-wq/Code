"""Custom Qt widgets for the Gaming HUD overlay."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QRectF, QTimer, pyqtProperty
from PyQt5.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QBrush,
)
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from gaming_hud import styles


# ── Utility ─────────────────────────────────────────────────────────────────

def make_separator() -> QFrame:
    """Create a styled horizontal separator line."""
    sep = QFrame()
    sep.setObjectName("separator")
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    return sep


def make_section_label(text: str) -> QLabel:
    """Create a small uppercase section header label."""
    label = QLabel(text)
    label.setObjectName("sectionLabel")
    font = label.font()
    font.setPixelSize(styles.FONT_SIZE_SMALL)
    font.setBold(True)
    label.setFont(font)
    label.setStyleSheet(f"color: {styles.TEXT_SECONDARY};")
    return label


# ── Usage Bar ───────────────────────────────────────────────────────────────

class UsageBar(QWidget):
    """A compact colored bar that fills based on a percentage value."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._percent = 0.0
        self._color = styles.BAR_LOW
        self.setFixedHeight(styles.BAR_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, percent: float, color: str | None = None):
        self._percent = max(0.0, min(100.0, percent))
        self._color = color or styles.get_bar_color(percent)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        r = self.rect().adjusted(0, 0, 0, 0)
        h = r.height()
        radius = styles.BAR_RADIUS

        # Background track
        path_bg = QPainterPath()
        path_bg.addRoundedRect(QRectF(r), radius, radius)
        p.fillPath(path_bg, QColor(styles.BG_TERTIARY))

        # Filled portion
        if self._percent > 0:
            fill_w = max(h, r.width() * self._percent / 100.0)
            fill_rect = QRectF(r.x(), r.y(), fill_w, h)
            path_fill = QPainterPath()
            path_fill.addRoundedRect(fill_rect, radius, radius)

            grad = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
            color = QColor(self._color)
            grad.setColorAt(0.0, color.darker(120))
            grad.setColorAt(1.0, color)
            p.fillPath(path_fill, QBrush(grad))

        p.end()


# ── Stat Row ────────────────────────────────────────────────────────────────

class StatRow(QWidget):
    """A single metric row: icon + label, value, and usage bar."""

    def __init__(self, icon: str, label: str, unit: str = "%", parent=None):
        super().__init__(parent)
        self._unit = unit

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Top row: label + value
        top = QHBoxLayout()
        top.setSpacing(6)

        self._icon_label = QLabel(f"{icon} {label}")
        self._icon_label.setObjectName("metricLabel")
        font = self._icon_label.font()
        font.setPixelSize(styles.FONT_SIZE_LABEL)
        self._icon_label.setFont(font)

        self._value_label = QLabel("--")
        self._value_label.setObjectName("valueLabel")
        self._value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vfont = self._value_label.font()
        vfont.setPixelSize(styles.FONT_SIZE_VALUE)
        vfont.setBold(True)
        vfont.setFamily("Consolas, 'Courier New', monospace")
        self._value_label.setFont(vfont)

        top.addWidget(self._icon_label)
        top.addStretch()
        top.addWidget(self._value_label)
        layout.addLayout(top)

        # Bar
        self._bar = UsageBar()
        layout.addWidget(self._bar)

    def set_value(self, value: float, color: str | None = None):
        if self._unit == "%":
            self._value_label.setText(f"{value:.0f}%")
        elif self._unit == "GB":
            self._value_label.setText(f"{value:.1f} GB")
        else:
            self._value_label.setText(f"{value:.0f}{self._unit}")
        self._bar.set_value(value if self._unit == "%" else 0, color)

    def set_value_text(self, text: str, bar_percent: float = 0,
                       color: str | None = None):
        self._value_label.setText(text)
        self._bar.set_value(bar_percent, color)

    def set_color(self, color: str):
        self._value_label.setStyleSheet(f"color: {color};")


# ── FPS Display ─────────────────────────────────────────────────────────────

class FPSDisplay(QWidget):
    """Large FPS counter with color-coded value."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        icon = QLabel("◎")
        icon.setStyleSheet(
            f"color: {styles.ACCENT_CYAN}; font-size: 16px;"
        )

        self._label = QLabel("FPS")
        self._label.setObjectName("metricLabel")
        f = self._label.font()
        f.setPixelSize(styles.FONT_SIZE_LABEL)
        self._label.setFont(f)

        self._value = QLabel("--")
        self._value.setObjectName("valueLabel")
        self._value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vf = QFont("Consolas, 'Courier New', monospace")
        vf.setPixelSize(20)
        vf.setBold(True)
        self._value.setFont(vf)
        self._value.setStyleSheet(f"color: {styles.ACCENT_GREEN};")

        layout.addWidget(icon)
        layout.addWidget(self._label)
        layout.addStretch()
        layout.addWidget(self._value)

    def set_fps(self, fps: int):
        self._value.setText(str(fps))
        if fps >= 60:
            color = styles.ACCENT_GREEN
        elif fps >= 30:
            color = styles.ACCENT_ORANGE
        else:
            color = styles.ACCENT_RED
        self._value.setStyleSheet(f"color: {color};")


# ── Network Display ─────────────────────────────────────────────────────────

class NetworkDisplay(QWidget):
    """Shows ping latency and upload/download throughput."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Ping row
        ping_row = QHBoxLayout()
        ping_row.setSpacing(6)

        self._ping_icon = QLabel("●")
        self._ping_icon.setStyleSheet(
            f"color: {styles.ACCENT_GREEN}; font-size: 10px;"
        )
        self._ping_label = QLabel("PING")
        self._ping_label.setObjectName("metricLabel")
        f = self._ping_label.font()
        f.setPixelSize(styles.FONT_SIZE_LABEL)
        self._ping_label.setFont(f)

        self._ping_value = QLabel("--")
        self._ping_value.setObjectName("valueLabel")
        self._ping_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vf = QFont("Consolas, 'Courier New', monospace")
        vf.setPixelSize(styles.FONT_SIZE_VALUE)
        vf.setBold(True)
        self._ping_value.setFont(vf)

        ping_row.addWidget(self._ping_icon)
        ping_row.addWidget(self._ping_label)
        ping_row.addStretch()
        ping_row.addWidget(self._ping_value)
        layout.addLayout(ping_row)

        # Throughput row
        tp_row = QHBoxLayout()
        tp_row.setSpacing(8)

        self._upload_label = QLabel("↑ --")
        self._upload_label.setStyleSheet(
            f"color: {styles.ACCENT_CYAN}; font-size: {styles.FONT_SIZE_SMALL}px;"
            f" font-family: Consolas, monospace;"
        )
        self._download_label = QLabel("↓ --")
        self._download_label.setStyleSheet(
            f"color: {styles.ACCENT_GREEN}; font-size: {styles.FONT_SIZE_SMALL}px;"
            f" font-family: Consolas, monospace;"
        )

        tp_row.addWidget(self._upload_label)
        tp_row.addStretch()
        tp_row.addWidget(self._download_label)
        layout.addLayout(tp_row)

    @staticmethod
    def _format_speed(bytes_per_sec: float) -> str:
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"

    def set_data(self, ping_ms: float | None, upload: float, download: float):
        if ping_ms is not None:
            self._ping_value.setText(f"{ping_ms:.0f} ms")
            if ping_ms < 50:
                color = styles.ACCENT_GREEN
                dot_color = styles.ACCENT_GREEN
            elif ping_ms < 100:
                color = styles.ACCENT_ORANGE
                dot_color = styles.ACCENT_ORANGE
            else:
                color = styles.ACCENT_RED
                dot_color = styles.ACCENT_RED
            self._ping_value.setStyleSheet(f"color: {color};")
            self._ping_icon.setStyleSheet(f"color: {dot_color}; font-size: 10px;")
        else:
            self._ping_value.setText("N/A")
            self._ping_value.setStyleSheet(f"color: {styles.TEXT_DIM};")
            self._ping_icon.setStyleSheet(
                f"color: {styles.TEXT_DIM}; font-size: 10px;"
            )

        self._upload_label.setText(f"↑ {self._format_speed(upload)}")
        self._download_label.setText(f"↓ {self._format_speed(download)}")


# ── Media Display ───────────────────────────────────────────────────────────

class MediaDisplay(QWidget):
    """Shows currently playing media info."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.setSpacing(4)

        icon = QLabel("♫")
        icon.setStyleSheet(
            f"color: {styles.ACCENT_GREEN}; font-size: 14px;"
        )
        source_label = QLabel("NOW PLAYING")
        source_label.setObjectName("sectionLabel")
        f = source_label.font()
        f.setPixelSize(styles.FONT_SIZE_SMALL)
        f.setBold(True)
        source_label.setFont(f)
        self._source = source_label

        header.addWidget(icon)
        header.addWidget(source_label)
        header.addStretch()
        layout.addLayout(header)

        self._title = QLabel("No media detected")
        self._title.setObjectName("mediaLabel")
        self._title.setWordWrap(True)
        tf = self._title.font()
        tf.setPixelSize(styles.FONT_SIZE_LABEL)
        self._title.setFont(tf)
        self._title.setStyleSheet(f"color: {styles.TEXT_DIM};")
        layout.addWidget(self._title)

    def set_media(self, playing: bool, title: str, source: str):
        if playing and title:
            self._source.setText(source.upper() if source else "NOW PLAYING")
            self._title.setText(title)
            self._title.setStyleSheet(f"color: {styles.TEXT_PRIMARY};")
        else:
            self._source.setText("NOW PLAYING")
            self._title.setText("No media detected")
            self._title.setStyleSheet(f"color: {styles.TEXT_DIM};")


# ── Key Visualizer ──────────────────────────────────────────────────────────

class KeyButton(QWidget):
    """A single key in the WASD visualizer that lights up when pressed."""

    def __init__(self, label: str, width: int = styles.KEY_SIZE,
                 height: int = styles.KEY_SIZE, parent=None):
        super().__init__(parent)
        self._label = label
        self._active = False
        self._glow = 0.0
        self.setFixedSize(width, height)

        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(16)  # ~60fps animation
        self._glow_timer.timeout.connect(self._animate_glow)

    @pyqtProperty(float)
    def glow(self):
        return self._glow

    @glow.setter
    def glow(self, val):
        self._glow = val
        self.update()

    def set_active(self, active: bool):
        self._active = active
        self._glow_timer.start()

    def _animate_glow(self):
        target = 1.0 if self._active else 0.0
        diff = target - self._glow
        if abs(diff) < 0.02:
            self._glow = target
            self._glow_timer.stop()
        else:
            self._glow += diff * 0.3
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        radius = styles.KEY_RADIUS

        # Interpolate colors based on glow
        g = self._glow
        bg = self._lerp_color(styles.KEY_INACTIVE_BG, styles.KEY_ACTIVE_BG, g)
        border = self._lerp_color(
            styles.KEY_INACTIVE_BORDER, styles.KEY_ACTIVE_BORDER, g
        )
        text_color = self._lerp_color(
            styles.KEY_INACTIVE_TEXT, styles.KEY_ACTIVE_TEXT, g
        )

        # Glow effect (outer)
        if g > 0.1:
            glow_color = QColor(styles.ACCENT_CYAN)
            glow_color.setAlphaF(g * 0.15)
            glow_rect = QRectF(rect).adjusted(-2, -2, 2, 2)
            glow_path = QPainterPath()
            glow_path.addRoundedRect(glow_rect, radius + 2, radius + 2)
            p.fillPath(glow_path, glow_color)

        # Background
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        p.fillPath(path, QColor(bg))

        # Border
        pen = QPen(QColor(border), 1.5)
        p.setPen(pen)
        p.drawRoundedRect(rect, radius, radius)

        # Label text
        p.setPen(QColor(text_color))
        font = QFont("Consolas, 'Courier New', monospace")
        font.setPixelSize(styles.FONT_SIZE_KEY)
        font.setBold(True)
        p.setFont(font)
        p.drawText(rect, Qt.AlignCenter, self._label)

        p.end()

    @staticmethod
    def _lerp_color(c1_hex: str, c2_hex: str, t: float) -> str:
        c1 = QColor(c1_hex)
        c2 = QColor(c2_hex)
        r = int(c1.red() + (c2.red() - c1.red()) * t)
        g = int(c1.green() + (c2.green() - c1.green()) * t)
        b = int(c1.blue() + (c2.blue() - c1.blue()) * t)
        return QColor(r, g, b).name()


class KeyVisualizer(QWidget):
    """WASD + Space key visualizer with animated glow effects."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignHCenter)

        # W row (centered)
        w_row = QHBoxLayout()
        w_row.setAlignment(Qt.AlignHCenter)
        w_row.setSpacing(3)
        self.key_w = KeyButton("W")
        w_row.addWidget(self.key_w)
        layout.addLayout(w_row)

        # ASD row (centered)
        asd_row = QHBoxLayout()
        asd_row.setAlignment(Qt.AlignHCenter)
        asd_row.setSpacing(3)
        self.key_a = KeyButton("A")
        self.key_s = KeyButton("S")
        self.key_d = KeyButton("D")
        asd_row.addWidget(self.key_a)
        asd_row.addWidget(self.key_s)
        asd_row.addWidget(self.key_d)
        layout.addLayout(asd_row)

        # Space bar
        space_row = QHBoxLayout()
        space_row.setAlignment(Qt.AlignHCenter)
        space_row.setSpacing(3)
        space_width = styles.KEY_SIZE * 3 + 6  # Width of 3 keys + spacing
        self.key_space = KeyButton("SPACE", width=space_width, height=28)
        space_row.addWidget(self.key_space)
        layout.addLayout(space_row)

        self._keys = {
            "w": self.key_w,
            "a": self.key_a,
            "s": self.key_s,
            "d": self.key_d,
            "space": self.key_space,
        }

    def on_key_event(self, key_name: str, pressed: bool):
        key_widget = self._keys.get(key_name)
        if key_widget:
            key_widget.set_active(pressed)
