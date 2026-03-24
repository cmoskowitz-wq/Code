"""
SmartTrade Insights - Dark Terminal Theme
Bloomberg/TradingView-inspired colour palette.
"""

DARK_THEME = """
/* ── Base ─────────────────────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: 'Segoe UI', 'SF Pro Display', Arial, sans-serif;
    font-size: 13px;
}

QSplitter::handle {
    background-color: #30363d;
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
QFrame#sidebar {
    background-color: #010409;
    border-right: 1px solid #21262d;
    min-width: 64px;
    max-width: 64px;
}

/* ── Sidebar nav buttons ──────────────────────────────────────────────── */
QPushButton#nav_btn {
    background-color: transparent;
    border: none;
    color: #8b949e;
    font-size: 22px;
    padding: 14px 0px;
    border-radius: 0px;
    text-align: center;
}
QPushButton#nav_btn:hover {
    color: #e6edf3;
    background-color: #161b22;
}
QPushButton#nav_btn[active="true"] {
    color: #58a6ff;
    background-color: #0d1117;
    border-left: 3px solid #58a6ff;
}

/* ── Cards / Panels ───────────────────────────────────────────────────── */
QFrame#card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
}
QFrame#card:hover {
    border: 1px solid #58a6ff;
}

QFrame#metric_card {
    background-color: #1c2128;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px;
}

/* ── Labels ───────────────────────────────────────────────────────────── */
QLabel#ticker_label {
    color: #e6edf3;
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 1px;
}
QLabel#price_label {
    color: #e6edf3;
    font-size: 24px;
    font-weight: bold;
}
QLabel#change_pos {
    color: #3fb950;
    font-size: 13px;
    font-weight: 600;
}
QLabel#change_neg {
    color: #f85149;
    font-size: 13px;
    font-weight: 600;
}
QLabel#section_title {
    color: #8b949e;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}
QLabel#app_title {
    color: #58a6ff;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
}
QLabel#stat_label {
    color: #8b949e;
    font-size: 11px;
}
QLabel#stat_value {
    color: #e6edf3;
    font-size: 13px;
    font-weight: 600;
}

/* ── Signal badges ────────────────────────────────────────────────────── */
QLabel#badge_buy {
    background-color: #1a4d2e;
    color: #3fb950;
    border: 1px solid #3fb950;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#badge_sell {
    background-color: #4d1a1a;
    color: #f85149;
    border: 1px solid #f85149;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#badge_hold {
    background-color: #4d3a0a;
    color: #d29922;
    border: 1px solid #d29922;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #58a6ff;
}
QPushButton:pressed {
    background-color: #161b22;
}
QPushButton:disabled {
    color: #6e7681;
    border-color: #21262d;
}

QPushButton#primary_btn {
    background-color: #1f6feb;
    color: #ffffff;
    border: 1px solid #1f6feb;
    padding: 8px 20px;
}
QPushButton#primary_btn:hover {
    background-color: #388bfd;
    border-color: #388bfd;
}

QPushButton#danger_btn {
    background-color: #b91c1c;
    color: #ffffff;
    border: 1px solid #b91c1c;
}
QPushButton#danger_btn:hover {
    background-color: #dc2626;
}

QPushButton#success_btn {
    background-color: #15803d;
    color: #ffffff;
    border: 1px solid #15803d;
}
QPushButton#success_btn:hover {
    background-color: #16a34a;
}

QPushButton#refresh_btn {
    background-color: transparent;
    border: 1px solid #30363d;
    color: #8b949e;
    padding: 4px 12px;
    font-size: 18px;
    border-radius: 6px;
}
QPushButton#refresh_btn:hover {
    color: #58a6ff;
    border-color: #58a6ff;
}

QPushButton#add_stock_btn {
    background-color: #1c2128;
    border: 2px dashed #30363d;
    color: #8b949e;
    border-radius: 8px;
    font-size: 28px;
    font-weight: 300;
}
QPushButton#add_stock_btn:hover {
    border-color: #58a6ff;
    color: #58a6ff;
    background-color: #1a3a5c;
}

/* ── Input fields ─────────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #1f6feb;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #58a6ff;
    outline: none;
}
QLineEdit::placeholder {
    color: #6e7681;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #21262d;
    border: none;
    width: 20px;
}

/* ── Dropdowns ────────────────────────────────────────────────────────── */
QComboBox {
    background-color: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    min-width: 120px;
}
QComboBox:hover {
    border-color: #58a6ff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #8b949e;
    margin-right: 6px;
}
QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #e6edf3;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
    outline: none;
}

/* ── Sliders ──────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 4px;
    background-color: #30363d;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #58a6ff;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background-color: #1f6feb;
    border-radius: 2px;
}

/* ── Tables ───────────────────────────────────────────────────────────── */
QTableWidget, QTableView {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #21262d;
    border-radius: 6px;
    gridline-color: #21262d;
    selection-background-color: #1f6feb;
    alternate-background-color: #161b22;
}
QTableWidget::item, QTableView::item {
    padding: 6px 8px;
    border: none;
}
QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    border: none;
    border-bottom: 1px solid #30363d;
    padding: 8px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* ── Scroll bars ──────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background-color: #0d1117;
    width: 8px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #8b949e;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background-color: #0d1117;
    height: 8px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #30363d;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Tab bar ──────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #30363d;
    background-color: #0d1117;
}
QTabBar::tab {
    background-color: #161b22;
    color: #8b949e;
    border: 1px solid #30363d;
    border-bottom: none;
    padding: 8px 20px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #0d1117;
    color: #e6edf3;
    border-bottom: 2px solid #58a6ff;
}
QTabBar::tab:hover {
    color: #e6edf3;
}

/* ── Status bar ───────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #161b22;
    color: #8b949e;
    border-top: 1px solid #21262d;
    font-size: 11px;
}
QStatusBar::item {
    border: none;
}

/* ── Progress bar ─────────────────────────────────────────────────────── */
QProgressBar {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    text-align: center;
    color: #e6edf3;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #1f6feb;
    border-radius: 3px;
}

/* ── Tooltip ──────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #161b22;
    color: #e6edf3;
    border: 1px solid #58a6ff;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}

/* ── Group boxes ──────────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 4px;
    color: #8b949e;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    top: -8px;
    padding: 0 4px;
    background-color: #0d1117;
}

/* ── Checkboxes ───────────────────────────────────────────────────────── */
QCheckBox {
    color: #e6edf3;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #30363d;
    border-radius: 3px;
    background-color: #0d1117;
}
QCheckBox::indicator:checked {
    background-color: #1f6feb;
    border-color: #1f6feb;
}
QCheckBox::indicator:hover {
    border-color: #58a6ff;
}

/* ── Menu ─────────────────────────────────────────────────────────────── */
QMenu {
    background-color: #161b22;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 3px;
}
QMenu::item:selected {
    background-color: #1f6feb;
}
QMenu::separator {
    height: 1px;
    background-color: #30363d;
    margin: 4px 0;
}

/* ── Divider line ─────────────────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    background-color: #21262d;
    border: none;
    max-height: 1px;
}
"""


def signal_badge_style(signal_type: str) -> str:
    """Return inline style string for a signal badge label."""
    styles = {
        "BUY": (
            "background-color: #1a4d2e; color: #3fb950; "
            "border: 1px solid #3fb950; border-radius: 4px; "
            "padding: 2px 10px; font-size: 12px; font-weight: bold; letter-spacing: 1px;"
        ),
        "SELL": (
            "background-color: #4d1a1a; color: #f85149; "
            "border: 1px solid #f85149; border-radius: 4px; "
            "padding: 2px 10px; font-size: 12px; font-weight: bold; letter-spacing: 1px;"
        ),
        "HOLD": (
            "background-color: #4d3a0a; color: #d29922; "
            "border: 1px solid #d29922; border-radius: 4px; "
            "padding: 2px 10px; font-size: 12px; font-weight: bold; letter-spacing: 1px;"
        ),
    }
    return styles.get(signal_type.upper(), styles["HOLD"])


def change_color(change_pct: float) -> str:
    return "#3fb950" if change_pct >= 0 else "#f85149"


def strength_color(strength: float) -> str:
    if strength >= 70:
        return "#3fb950"
    if strength >= 50:
        return "#d29922"
    return "#f85149"
