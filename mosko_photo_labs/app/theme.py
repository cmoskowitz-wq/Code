"""
theme.py — Mosko Photo Labs
Professional dark photographer theme (Lightroom-inspired).
"""

from app.constants import COLORS


def get_stylesheet() -> str:
    c = COLORS
    return f"""
/* ── Global ──────────────────────────────────────────────────────────── */
QWidget {{
    background-color: {c['bg_panel']};
    color: {c['text_primary']};
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    border: none;
    outline: none;
}}

QMainWindow {{
    background-color: {c['bg_dark']};
}}

/* ── Toolbar ─────────────────────────────────────────────────────────── */
QToolBar {{
    background-color: {c['bg_toolbar']};
    border-bottom: 1px solid {c['border']};
    padding: 4px 8px;
    spacing: 4px;
}}

QToolButton {{
    background-color: transparent;
    color: {c['text_secondary']};
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 500;
}}

QToolButton:hover {{
    background-color: {c['bg_hover']};
    color: {c['text_primary']};
    border-color: {c['border']};
}}

QToolButton:pressed, QToolButton:checked {{
    background-color: {c['accent_dim']};
    color: {c['accent_light']};
    border-color: {c['accent']};
}}

/* ── Menu Bar ────────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {c['bg_toolbar']};
    color: {c['text_primary']};
    border-bottom: 1px solid {c['border']};
    padding: 2px;
}}

QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 3px;
}}

QMenuBar::item:selected {{
    background-color: {c['bg_hover']};
    color: {c['accent_light']};
}}

QMenu {{
    background-color: {c['bg_card']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 4px 0;
}}

QMenu::item {{
    padding: 6px 20px 6px 12px;
    border-radius: 3px;
    margin: 1px 4px;
}}

QMenu::item:selected {{
    background-color: {c['bg_selected']};
    color: {c['accent_light']};
}}

QMenu::separator {{
    height: 1px;
    background-color: {c['border']};
    margin: 4px 8px;
}}

/* ── Status Bar ──────────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {c['bg_toolbar']};
    color: {c['text_secondary']};
    border-top: 1px solid {c['border']};
    font-size: 11px;
    padding: 2px 8px;
}}

QStatusBar::item {{
    border: none;
}}

/* ── Splitter ─────────────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {c['border']};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

/* ── Panels / Frames ──────────────────────────────────────────────────── */
QFrame#BrowserPanel, QFrame#PreviewPanel, QFrame#ExifPanel {{
    background-color: {c['bg_panel']};
    border: none;
}}

/* ── Labels ───────────────────────────────────────────────────────────── */
QLabel {{
    color: {c['text_primary']};
    background-color: transparent;
}}

QLabel#SectionHeader {{
    color: {c['accent_light']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 8px 0 4px 0;
    background-color: transparent;
}}

QLabel#PanelTitle {{
    color: {c['text_primary']};
    font-size: 12px;
    font-weight: 600;
    padding: 6px 0;
}}

QLabel#FieldLabel {{
    color: {c['text_secondary']};
    font-size: 12px;
    background-color: transparent;
}}

QLabel#CameraInfo {{
    color: {c['text_secondary']};
    font-size: 11px;
    background-color: transparent;
}}

QLabel#GpsLabel {{
    color: {c['success']};
    font-size: 11px;
    background-color: transparent;
}}

QLabel#Modified {{
    color: {c['modified']};
    font-size: 10px;
    font-weight: 700;
    background-color: transparent;
}}

/* ── Line Edits ──────────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: {c['bg_selected']};
}}

QLineEdit:focus {{
    border-color: {c['accent']};
    background-color: #2e2e2e;
}}

QLineEdit:disabled {{
    color: {c['text_disabled']};
    background-color: {c['bg_card']};
}}

QLineEdit[modified="true"] {{
    border-color: {c['modified']};
}}

/* ── Text Edit ──────────────────────────────────────────────────────── */
QTextEdit, QPlainTextEdit {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    padding: 6px;
    selection-background-color: {c['bg_selected']};
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {c['accent']};
}}

/* ── ComboBox ────────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    padding: 5px 8px;
    min-width: 80px;
}}

QComboBox:focus {{
    border-color: {c['accent']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c['text_secondary']};
    margin-right: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {c['bg_card']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    selection-background-color: {c['bg_selected']};
    outline: none;
}}

/* ── Push Buttons ────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: 500;
    min-width: 64px;
}}

QPushButton:hover {{
    background-color: {c['bg_hover']};
    border-color: {c['border_focus']};
    color: {c['accent_light']};
}}

QPushButton:pressed {{
    background-color: {c['accent_dim']};
    border-color: {c['accent']};
}}

QPushButton#AccentButton {{
    background-color: {c['accent']};
    color: #ffffff;
    border-color: {c['accent']};
    font-weight: 600;
}}

QPushButton#AccentButton:hover {{
    background-color: {c['accent_light']};
    border-color: {c['accent_light']};
}}

QPushButton#AccentButton:pressed {{
    background-color: {c['accent_dim']};
}}

QPushButton#DangerButton {{
    background-color: transparent;
    color: {c['error']};
    border-color: {c['error']};
}}

QPushButton#DangerButton:hover {{
    background-color: rgba(244,67,54,0.15);
}}

/* ── Scroll Area / Bar ───────────────────────────────────────────────── */
QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background-color: {c['bg_panel']};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {c['scrollbar_handle']};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {c['accent_dim']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    border: none;
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {c['bg_panel']};
    height: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: {c['scrollbar_handle']};
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
    border: none;
    width: 0;
}}

/* ── List Widget (file browser) ──────────────────────────────────────── */
QListWidget {{
    background-color: {c['bg_dark']};
    border: none;
    padding: 4px;
    outline: none;
}}

QListWidget::item {{
    color: {c['text_primary']};
    border-radius: 4px;
    padding: 4px;
    margin: 2px;
}}

QListWidget::item:hover {{
    background-color: {c['bg_hover']};
}}

QListWidget::item:selected {{
    background-color: {c['bg_selected']};
    color: {c['accent_light']};
}}

/* ── Table Widget (EXIF all-fields view) ─────────────────────────────── */
QTableWidget {{
    background-color: {c['bg_dark']};
    border: none;
    gridline-color: {c['border']};
    selection-background-color: {c['bg_selected']};
    outline: none;
}}

QTableWidget::item {{
    padding: 4px 8px;
    border-bottom: 1px solid {c['border']};
}}

QHeaderView::section {{
    background-color: {c['bg_card']};
    color: {c['text_secondary']};
    font-size: 11px;
    font-weight: 600;
    padding: 5px 8px;
    border: none;
    border-bottom: 1px solid {c['border']};
}}

/* ── Tab Widget ──────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background-color: {c['bg_panel']};
}}

QTabBar::tab {{
    background-color: transparent;
    color: {c['text_secondary']};
    border-bottom: 2px solid transparent;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    color: {c['accent_light']};
    border-bottom-color: {c['accent']};
}}

QTabBar::tab:hover:!selected {{
    color: {c['text_primary']};
}}

/* ── GroupBox ────────────────────────────────────────────────────────── */
QGroupBox {{
    color: {c['text_secondary']};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    border: 1px solid {c['border']};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    color: {c['accent']};
}}

/* ── ToolTip ──────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {c['bg_card']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}

/* ── Progress Bar ────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {c['bg_card']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    text-align: center;
    color: {c['text_primary']};
    height: 14px;
    font-size: 11px;
}}

QProgressBar::chunk {{
    background-color: {c['accent']};
    border-radius: 4px;
}}

/* ── CheckBox ────────────────────────────────────────────────────────── */
QCheckBox {{
    color: {c['text_primary']};
    spacing: 6px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {c['border']};
    border-radius: 3px;
    background-color: {c['bg_input']};
}}

QCheckBox::indicator:checked {{
    background-color: {c['accent']};
    border-color: {c['accent']};
}}

/* ── Splitter handle hover ───────────────────────────────────────────── */
QSplitter::handle:hover {{
    background-color: {c['accent_dim']};
}}

/* ── Dialog ──────────────────────────────────────────────────────────── */
QDialog {{
    background-color: {c['bg_panel']};
}}

/* ── Thumbnail label in browser ──────────────────────────────────────── */
QLabel#ThumbLabel {{
    background-color: {c['bg_dark']};
    border: 2px solid transparent;
    border-radius: 4px;
}}

QLabel#ThumbLabel[selected="true"] {{
    border-color: {c['accent']};
}}
"""
