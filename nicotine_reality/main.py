"""
main.py — Nicotine Reality: The Truth Behind the Smoke
Entry point. Builds the main window, navigation hub, and wires all modules.
"""

import sys
import os

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QColor, QPainter, QLinearGradient, QPen, QPainterPath
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QStackedWidget,
                              QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QFrame, QGridLayout, QScrollArea,
                              QGraphicsOpacityEffect, QSizePolicy)

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from modules.theme import (BG, SURFACE, CARD, ACCENT, ACCENT2, TEXT, TEXT_DIM,
                            WARNING, BORDER, HOVER_CARD, GLOBAL_STYLESHEET,
                            font, apply_dark_palette, fade_in)
from modules.start_screen import StartScreen
from modules.stories import Stories
from modules.body_simulator import BodySimulator
from modules.addiction_simulator import AddictionSimulator
from modules.graphic_reality import GraphicReality
from modules.cost_calculator import CostCalculator
from modules.myth_quiz import MythQuiz
from modules.personal_impact import PersonalImpact
from modules.shock_moments import ShockMomentManager


# ── Navigation hub card ────────────────────────────────────────────────────────

NAV_CARDS = [
    {
        "key":    "stories",
        "title":  "Real Stories",
        "icon":   "📖",
        "desc":   "5 fictional but realistic accounts of teen nicotine addiction",
        "color":  "#7c3aed",
    },
    {
        "key":    "body",
        "title":  "Your Body",
        "icon":   "🫁",
        "desc":   "Interactive organ damage simulator — slide to see what happens",
        "color":  "#dc2626",
    },
    {
        "key":    "addiction",
        "title":  "How Fast?",
        "icon":   "⏱",
        "desc":   "Choose a usage path and watch dependency form in real time",
        "color":  "#ea580c",
    },
    {
        "key":    "graphic",
        "title":  "Graphic Reality",
        "icon":   "🔬",
        "desc":   "Medical-accuracy visualizations of long-term nicotine damage",
        "color":  "#b91c1c",
    },
    {
        "key":    "cost",
        "title":  "The Real Cost",
        "icon":   "💸",
        "desc":   "See the lifetime financial cost and what you're giving up",
        "color":  "#b45309",
    },
    {
        "key":    "quiz",
        "title":  "Myth or Reality?",
        "icon":   "🧠",
        "desc":   "8-question quiz — separate fact from industry fiction",
        "color":  "#0369a1",
    },
    {
        "key":    "impact",
        "title":  "Your Impact",
        "icon":   "📊",
        "desc":   "Personalized health and financial projections based on your age",
        "color":  "#047857",
    },
]


class NavCard(QFrame):
    """Single module card on the navigation hub."""

    def __init__(self, data: dict, on_click):
        super().__init__()
        self._color = QColor(data["color"])
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        icon = QLabel(data["icon"])
        icon.setFont(font(22))
        icon.setStyleSheet("background:transparent;")
        top_row.addWidget(icon)
        top_row.addStretch()
        layout.addLayout(top_row)

        title = QLabel(data["title"])
        title.setFont(font(13, bold=True))
        title.setStyleSheet("background:transparent; color:#ffffff;")
        layout.addWidget(title)

        desc = QLabel(data["desc"])
        desc.setFont(font(9))
        desc.setStyleSheet(f"background:transparent; color:rgba(255,255,255,0.65);")
        desc.setWordWrap(True)
        layout.addWidget(desc, 1)

        self.mousePressEvent = lambda e: on_click()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        base = self._color
        if self._hovered:
            base = base.lighter(130)

        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, base.darker(80))
        grad.setColorAt(1, base.darker(120))

        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 8, 8)
        p.fillPath(path, grad)

        if self._hovered:
            p.setPen(QPen(base.lighter(160), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(1, 1, w - 2, h - 2, 7, 7)

        p.end()
        super().paintEvent(event)


class NavHub(QWidget):
    """The main navigation screen with 7 module cards."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(14)

        # Header
        header_row = QHBoxLayout()
        logo = QLabel("NICOTINE REALITY")
        logo.setFont(font(13, bold=True))
        logo.setStyleSheet(f"color:{ACCENT}; letter-spacing:3px;")
        header_row.addWidget(logo)
        header_row.addStretch()
        root.addLayout(header_row)

        title = QLabel("Choose an Experience")
        title.setFont(font(22, bold=True))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        subtitle = QLabel(
            "Each module reveals a different dimension of what nicotine does to your body, mind, and future."
        )
        subtitle.setFont(font(11))
        subtitle.setStyleSheet(f"color:{TEXT_DIM};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        # Card grid
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)

        for i, card_data in enumerate(NAV_CARDS):
            key = card_data["key"]
            card = NavCard(card_data, on_click=lambda k=key: self.main_window.go_to_screen(k))
            grid.addWidget(card, i // 3, i % 3)

        root.addWidget(grid_widget, 1)

        # Footer stat
        footer = QLabel(
            "90% of adult smokers started before age 18.  |  "
            "Every module here is backed by peer-reviewed research."
        )
        footer.setFont(font(9))
        footer.setStyleSheet(f"color:{TEXT_DIM};")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)


# ── Main Window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nicotine Reality — The Truth Behind the Smoke")
        self.resize(1100, 700)
        self.setMinimumSize(900, 600)

        self._current_screen = "start"
        self._screen_cache: dict[str, QWidget] = {}

        # Central stacked widget
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Build start screen immediately
        start = StartScreen(self)
        self._screen_cache["start"] = start
        self._stack.addWidget(start)
        self._stack.setCurrentWidget(start)

        # Shock moments (starts after a delay)
        self._shock_manager = ShockMomentManager(self)
        QTimer.singleShot(30_000, self._shock_manager.start)   # start after 30s

    def go_to_screen(self, name: str):
        self._current_screen = name

        if name in self._screen_cache:
            widget = self._screen_cache[name]
        else:
            widget = self._build_screen(name)
            if widget is None:
                return
            self._screen_cache[name] = widget
            self._stack.addWidget(widget)

        # Fade transition
        old = self._stack.currentWidget()
        if old and old is not widget:
            effect = QGraphicsOpacityEffect(old)
            old.setGraphicsEffect(effect)
            out = QPropertyAnimation(effect, b"opacity", self)
            out.setDuration(150)
            out.setStartValue(1.0)
            out.setEndValue(0.0)
            out.setEasingCurve(QEasingCurve.Type.InOutQuad)
            def _switch(w=widget):
                self._stack.setCurrentWidget(w)
                fade_in(w, duration=250)
            out.finished.connect(_switch)
            out.start()
            self._out_anim = out
        else:
            self._stack.setCurrentWidget(widget)
            fade_in(widget, duration=250)

    def _build_screen(self, name: str):
        builders = {
            "nav":       lambda: NavHub(self),
            "stories":   lambda: Stories(self),
            "body":      lambda: BodySimulator(self),
            "addiction": lambda: AddictionSimulator(self),
            "graphic":   lambda: GraphicReality(self),
            "cost":      lambda: CostCalculator(self),
            "quiz":      lambda: MythQuiz(self),
            "impact":    lambda: PersonalImpact(self),
        }
        builder = builders.get(name)
        if builder:
            return builder()
        return None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reposition any active shock popups
        for child in self.findChildren(QWidget):
            if hasattr(child, "_reposition"):
                child._reposition()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Nicotine Reality")
    app.setApplicationVersion("1.0")

    apply_dark_palette(app)
    app.setStyleSheet(GLOBAL_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
