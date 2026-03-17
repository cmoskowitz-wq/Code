"""
theme.py — Centralized design system for Nicotine Reality.
All colors, fonts, stylesheets, and animation helpers live here.
"""

from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QPoint, QRect
from PyQt6.QtGui import QColor, QFont, QPalette, QLinearGradient
from PyQt6.QtWidgets import QApplication, QGraphicsOpacityEffect


# ── Color palette ──────────────────────────────────────────────────────────────
BG         = "#0a0a0a"
SURFACE    = "#1a1a1a"
CARD       = "#1e1e1e"
ACCENT     = "#cc0000"
ACCENT2    = "#ff3333"
TEXT       = "#ffffff"
TEXT_DIM   = "#aaaaaa"
WARNING    = "#ff6600"
SUCCESS    = "#00aa44"
BORDER     = "#2a2a2a"
HOVER_CARD = "#252525"

# ── Fonts ──────────────────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI, Helvetica Neue, Arial, sans-serif"


def font(size: int, bold: bool = False, italic: bool = False) -> QFont:
    f = QFont("Segoe UI")
    f.setPointSize(size)
    f.setBold(bold)
    f.setItalic(italic)
    if not f.exactMatch():
        f.setFamily("Helvetica Neue")
    if not f.exactMatch():
        f.setFamily("Arial")
    return f


# ── Global stylesheet ──────────────────────────────────────────────────────────
GLOBAL_STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: {FONT_FAMILY};
}}

QScrollArea {{
    border: none;
    background-color: {BG};
}}

QScrollBar:vertical {{
    background: {SURFACE};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {ACCENT};
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {SURFACE};
    height: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: {ACCENT};
    border-radius: 4px;
    min-width: 20px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QLabel {{
    background: transparent;
    color: {TEXT};
}}

QPushButton {{
    background-color: {ACCENT};
    color: {TEXT};
    border: none;
    border-radius: 4px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 0.5px;
}}

QPushButton:hover {{
    background-color: {ACCENT2};
}}

QPushButton:pressed {{
    background-color: #990000;
}}

QPushButton#secondary {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    color: {TEXT_DIM};
}}

QPushButton#secondary:hover {{
    background-color: {CARD};
    color: {TEXT};
    border-color: {ACCENT};
}}

QPushButton#back_btn {{
    background-color: transparent;
    border: 1px solid {BORDER};
    color: {TEXT_DIM};
    padding: 6px 14px;
    font-size: 12px;
    font-weight: normal;
    border-radius: 4px;
}}

QPushButton#back_btn:hover {{
    border-color: {ACCENT};
    color: {TEXT};
    background-color: {SURFACE};
}}

QSlider::groove:horizontal {{
    background: {SURFACE};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}

QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 3px;
}}

QProgressBar {{
    background: {SURFACE};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 3px;
}}

QLineEdit {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    color: {TEXT};
    padding: 8px 12px;
    font-size: 13px;
}}

QLineEdit:focus {{
    border-color: {ACCENT};
}}

QComboBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    color: {TEXT};
    padding: 8px 12px;
    font-size: 13px;
}}

QComboBox:focus {{
    border-color: {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background: {SURFACE};
    color: {TEXT};
    selection-background-color: {ACCENT};
    border: 1px solid {BORDER};
}}
"""


def apply_dark_palette(app: QApplication) -> None:
    """Apply the dark QPalette to the entire application."""
    palette = QPalette()
    bg = QColor(BG)
    surface = QColor(SURFACE)
    text = QColor(TEXT)
    text_dim = QColor(TEXT_DIM)
    accent = QColor(ACCENT)

    palette.setColor(QPalette.ColorRole.Window, bg)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, surface)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(CARD))
    palette.setColor(QPalette.ColorRole.ToolTipBase, surface)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, surface)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(ACCENT2))
    palette.setColor(QPalette.ColorRole.Link, accent)
    palette.setColor(QPalette.ColorRole.Highlight, accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, text)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, text_dim)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, text_dim)

    app.setPalette(palette)


def fade_in(widget, duration: int = 400) -> QPropertyAnimation:
    """Fade a widget in using QGraphicsOpacityEffect."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    anim.start()
    return anim


def fade_out(widget, duration: int = 300) -> QPropertyAnimation:
    """Fade a widget out using QGraphicsOpacityEffect."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    anim.start()
    return anim


def card_stylesheet(hover: bool = False) -> str:
    bg = HOVER_CARD if hover else CARD
    return f"""
        background-color: {bg};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 16px;
    """
