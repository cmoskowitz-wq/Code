"""
start_screen.py — Animated opening screen for Nicotine Reality.
"""

from PyQt6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve,
                           QSequentialAnimationGroup, pyqtProperty)
from PyQt6.QtGui import (QPainter, QColor, QLinearGradient, QFont,
                          QRadialGradient, QPen)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QDialog, QDialogButtonBox, QTextEdit,
                              QGraphicsOpacityEffect, QSizePolicy)
import modules.theme as T
import math


class SmokeBackground(QWidget):
    """Slowly shifting dark gradient background simulating smoke."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self):
        self._offset = (self._offset + 0.003) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Base black fill
        p.fillRect(0, 0, w, h, QColor("#0a0a0a"))

        # Animated radial smoke blobs
        for i, (cx_frac, cy_frac, r_frac, alpha) in enumerate([
            (0.2, 0.3, 0.45, 30),
            (0.8, 0.6, 0.4, 25),
            (0.5, 0.5, 0.55, 20),
            (0.1, 0.8, 0.35, 18),
            (0.9, 0.2, 0.38, 22),
        ]):
            shift_x = math.sin(self._offset + i * 1.2) * 0.06
            shift_y = math.cos(self._offset + i * 0.9) * 0.05
            cx = int((cx_frac + shift_x) * w)
            cy = int((cy_frac + shift_y) * h)
            r = int(r_frac * max(w, h))

            grad = QRadialGradient(cx, cy, r)
            grad.setColorAt(0, QColor(40, 40, 50, alpha))
            grad.setColorAt(1, QColor(10, 10, 10, 0))
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)


class PulsingLine(QWidget):
    """A red horizontal line that pulses in opacity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(4)
        self._alpha = 255
        self._direction = -1
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def _tick(self):
        self._alpha += self._direction * 6
        if self._alpha <= 80:
            self._alpha = 80
            self._direction = 1
        elif self._alpha >= 255:
            self._alpha = 255
            self._direction = -1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        color = QColor(204, 0, 0, self._alpha)
        p.fillRect(0, 0, self.width(), self.height(), color)


class AnimatedTextLabel(QWidget):
    """Displays text that fades in word-by-word."""

    def __init__(self, lines: list, parent=None):
        super().__init__(parent)
        self._lines = lines          # list of str, each a phase
        self._current_phase = 0
        self._displayed_words = []
        self._all_words = []
        self._word_index = 0
        self._finished = False

        self._label = QLabel("", self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setFont(T.font(28, bold=True))
        self._label.setStyleSheet(f"color: {T.TEXT}; background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._word_timer = QTimer(self)
        self._word_timer.timeout.connect(self._show_next_word)
        self._pause_timer = QTimer(self)
        self._pause_timer.setSingleShot(True)
        self._pause_timer.timeout.connect(self._next_phase)

    def start_animation(self):
        self._current_phase = 0
        self._start_phase()

    def _start_phase(self):
        if self._current_phase >= len(self._lines):
            self._finished = True
            return
        self._all_words = self._lines[self._current_phase].split()
        self._displayed_words = []
        self._word_index = 0
        self._word_timer.start(160)

    def _show_next_word(self):
        if self._word_index < len(self._all_words):
            self._displayed_words.append(self._all_words[self._word_index])
            self._word_index += 1
            # Show all phases concatenated so far with dim old text
            self._update_display()
        else:
            self._word_timer.stop()
            self._pause_timer.start(1400)

    def _update_display(self):
        text = " ".join(self._displayed_words)
        self._label.setText(text)

    def _next_phase(self):
        self._current_phase += 1
        if self._current_phase < len(self._lines):
            # Fade out old text, show new
            self._label.setText("")
            QTimer.singleShot(300, self._start_phase)
        else:
            self._finished = True


class WhyMattersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Why This Matters")
        self.setModal(True)
        self.setFixedSize(520, 360)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {T.SURFACE};
                border: 1px solid {T.BORDER};
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
                color: {T.TEXT};
            }}
            QTextEdit {{
                background: {T.CARD};
                color: {T.TEXT_DIM};
                border: none;
                border-radius: 4px;
                font-size: 13px;
                padding: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 20)
        layout.setSpacing(16)

        title = QLabel("Why This App Exists")
        title.setFont(T.font(18, bold=True))
        title.setStyleSheet(f"color: {T.ACCENT2}; background: transparent;")
        layout.addWidget(title)

        body = QTextEdit()
        body.setReadOnly(True)
        body.setPlainText(
            "Every year, thousands of teenagers begin using nicotine products — most "
            "believing they can stop whenever they want.\n\n"
            "This app is built around one goal: to show you, without filters, what "
            "nicotine actually does. Not the advertising. Not the social media version. "
            "The real version — what happens to real bodies, real brains, and real lives.\n\n"
            "The stories are fictional composites based on documented clinical cases. "
            "The science is current. The consequences are real.\n\n"
            "You deserve accurate information. This is it."
        )
        layout.addWidget(body)

        btn = QPushButton("Close")
        btn.setFixedWidth(100)
        btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn)
        layout.addLayout(btn_row)


class StartScreen(QWidget):
    def __init__(self, nav_callback, parent=None):
        super().__init__(parent)
        self._nav = nav_callback

        # Smoke background
        self._smoke = SmokeBackground(self)
        self._smoke.resize(self.size())

        # Central overlay layout
        self._overlay = QWidget(self)
        self._overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        overlay_layout = QVBoxLayout(self._overlay)
        overlay_layout.setContentsMargins(60, 0, 60, 0)
        overlay_layout.setSpacing(0)
        overlay_layout.addStretch(2)

        # Animated text
        self._text_widget = AnimatedTextLabel(
            ["This is not a game.", "This is what nicotine does."],
            self
        )
        self._text_widget.setMinimumHeight(80)
        overlay_layout.addWidget(self._text_widget)

        overlay_layout.addSpacing(20)

        # Pulsing line
        self._pulse_line = PulsingLine(self)
        self._pulse_line.setFixedWidth(300)
        line_row = QHBoxLayout()
        line_row.addStretch()
        line_row.addWidget(self._pulse_line)
        line_row.addStretch()
        overlay_layout.addLayout(line_row)

        overlay_layout.addSpacing(50)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(20)
        btn_row.addStretch()

        self._enter_btn = QPushButton("Enter Experience")
        self._enter_btn.setFixedSize(200, 48)
        self._enter_btn.setFont(T.font(13, bold=True))
        self._enter_btn.clicked.connect(lambda: self._nav("nav_hub"))

        self._why_btn = QPushButton("Why This Matters")
        self._why_btn.setObjectName("secondary")
        self._why_btn.setFixedSize(200, 48)
        self._why_btn.setFont(T.font(13))
        self._why_btn.clicked.connect(self._show_why)

        btn_row.addWidget(self._enter_btn)
        btn_row.addWidget(self._why_btn)
        btn_row.addStretch()
        overlay_layout.addLayout(btn_row)

        overlay_layout.addStretch(3)

        # Fade-in effect on overlay
        self._opacity_effect = QGraphicsOpacityEffect(self._overlay)
        self._overlay.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0)

        # Timer to start animation after smoke renders
        QTimer.singleShot(300, self._start_intro)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._smoke.resize(self.size())
        self._overlay.resize(self.size())

    def _start_intro(self):
        anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        anim.setDuration(800)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.finished.connect(self._text_widget.start_animation)
        anim.start()
        self._intro_anim = anim  # keep reference

    def _show_why(self):
        dlg = WhyMattersDialog(self)
        dlg.exec()
