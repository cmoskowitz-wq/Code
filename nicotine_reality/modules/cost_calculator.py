"""
cost_calculator.py — Real-time financial cost visualizer.
Shows how much money nicotine use costs over time, and what it could buy instead.
"""

import math
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFont
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QSlider, QComboBox,
                              QSizePolicy, QScrollArea, QGridLayout,
                              QGraphicsOpacityEffect)
from modules.theme import (BG, SURFACE, CARD, ACCENT, ACCENT2, TEXT, TEXT_DIM,
                            WARNING, SUCCESS, BORDER, font, fade_in)


# ── Product definitions ────────────────────────────────────────────────────────

PRODUCTS = {
    "Cigarettes (pack/day)":   {"daily_cost": 12.0,  "unit": "pack"},
    "Vape pods (1/day)":       {"daily_cost": 4.50,  "unit": "pod"},
    "Vape pods (2/day)":       {"daily_cost": 9.00,  "unit": "2 pods"},
    "Disposable vapes (1/wk)": {"daily_cost": 3.00,  "unit": "disposable"},
    "Disposable vapes (3/wk)": {"daily_cost": 9.00,  "unit": "3 disposables"},
    "Nicotine pouches (1/day)": {"daily_cost": 2.50, "unit": "pouch tin"},
}

# What you could have bought instead
EQUIVALENTS = [
    {"name": "Spotify months",     "cost": 11.99,   "emoji": "🎵"},
    {"name": "Movie tickets",      "cost": 14.00,   "emoji": "🎬"},
    {"name": "Concert tickets",    "cost": 80.00,   "emoji": "🎤"},
    {"name": "Video games",        "cost": 60.00,   "emoji": "🎮"},
    {"name": "Gaming consoles",    "cost": 500.00,  "emoji": "🕹"},
    {"name": "Pairs of sneakers",  "cost": 120.00,  "emoji": "👟"},
    {"name": "Flights (domestic)", "cost": 250.00,  "emoji": "✈️"},
    {"name": "Laptops",            "cost": 800.00,  "emoji": "💻"},
    {"name": "Weekend trips",      "cost": 350.00,  "emoji": "🏖"},
    {"name": "Months of groceries","cost": 400.00,  "emoji": "🛒"},
    {"name": "Driving lessons",    "cost": 65.00,   "emoji": "🚗"},
    {"name": "Gym memberships",    "cost": 30.00,   "emoji": "💪"},
]


# ── Animated number display ───────────────────────────────────────────────────

class AnimatedNumber(QLabel):
    """Label that animates to a new value."""
    def __init__(self, prefix="$", suffix="", parent=None):
        super().__init__(parent)
        self._prefix = prefix
        self._suffix = suffix
        self._current = 0.0
        self._target = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self.setText(f"{self._prefix}0{self._suffix}")

    def set_value(self, value: float):
        self._target = value
        if not self._timer.isActive():
            self._timer.start(16)

    def _step(self):
        diff = self._target - self._current
        if abs(diff) < 0.5:
            self._current = self._target
            self._timer.stop()
        else:
            self._current += diff * 0.12
        if self._current >= 1000:
            text = f"{self._prefix}{self._current:,.0f}{self._suffix}"
        else:
            text = f"{self._prefix}{self._current:.2f}{self._suffix}"
        self.setText(text)


# ── Cost breakdown row ────────────────────────────────────────────────────────

class CostRow(QFrame):
    def __init__(self, label: str):
        super().__init__()
        self.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:6px;"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)

        self.label = QLabel(label)
        self.label.setFont(font(11))
        self.label.setStyleSheet(f"color:{TEXT_DIM};")
        layout.addWidget(self.label)
        layout.addStretch()

        self.value = AnimatedNumber()
        self.value.setFont(font(14, bold=True))
        self.value.setStyleSheet(f"color:{WARNING};")
        layout.addWidget(self.value)

    def update_value(self, amount: float):
        self.value.set_value(amount)


# ── Equivalent purchase card ──────────────────────────────────────────────────

class EquivCard(QFrame):
    def __init__(self, data: dict, count: int):
        super().__init__()
        self.setStyleSheet(
            f"background:{SURFACE}; border:1px solid {BORDER}; border-radius:6px;"
        )
        self.setFixedHeight(70)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        emoji_lbl = QLabel(f"{data['emoji']}  ×{count:,}")
        emoji_lbl.setFont(font(13, bold=True))
        emoji_lbl.setStyleSheet(f"color:{ACCENT2};")
        layout.addWidget(emoji_lbl)

        name_lbl = QLabel(data["name"])
        name_lbl.setFont(font(9))
        name_lbl.setStyleSheet(f"color:{TEXT_DIM};")
        layout.addWidget(name_lbl)

        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        self._effect = effect

    def show_animated(self, delay: int = 0):
        def start():
            anim = QPropertyAnimation(self._effect, b"opacity", self)
            anim.setDuration(400)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            anim.start()
            self._anim = anim
        QTimer.singleShot(delay, start)


# ── Main CostCalculator screen ────────────────────────────────────────────────

class CostCalculator(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._daily_cost = 4.50
        self._equiv_cards = []
        self._build_ui()
        self._update_costs()
        fade_in(self)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(12)

        # Back + title
        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("back_btn")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(lambda: self.main_window.go_to_screen("nav"))
        top.addWidget(back_btn)
        top.addStretch()
        title = QLabel("The Real Cost")
        title.setFont(font(18, bold=True))
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)

        subtitle = QLabel("See exactly how much nicotine habits cost — and what you're giving up.")
        subtitle.setFont(font(11))
        subtitle.setStyleSheet(f"color:{TEXT_DIM};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(subtitle)

        # Main layout: left controls, right breakdown
        main_row = QHBoxLayout()
        main_row.setSpacing(16)

        # Left: inputs
        left = QVBoxLayout()
        left.setSpacing(10)

        input_frame = QFrame()
        input_frame.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:8px;"
        )
        input_frame.setFixedWidth(280)
        inf = QVBoxLayout(input_frame)
        inf.setContentsMargins(16, 14, 16, 14)
        inf.setSpacing(12)

        inf.addWidget(QLabel("Product type:"))
        self.product_combo = QComboBox()
        for name in PRODUCTS:
            self.product_combo.addItem(name)
        self.product_combo.currentTextChanged.connect(self._on_product_change)
        inf.addWidget(self.product_combo)

        inf.addWidget(QLabel("Units per day:"))
        units_row = QHBoxLayout()
        self.units_slider = QSlider(Qt.Orientation.Horizontal)
        self.units_slider.setRange(1, 10)
        self.units_slider.setValue(1)
        self.units_val = QLabel("1")
        self.units_val.setFont(font(11, bold=True))
        self.units_val.setStyleSheet(f"color:{ACCENT};")
        self.units_val.setFixedWidth(24)
        units_row.addWidget(self.units_slider, 1)
        units_row.addWidget(self.units_val)
        inf.addLayout(units_row)
        self.units_slider.valueChanged.connect(self._on_units_change)

        # Daily cost display
        daily_frame = QFrame()
        daily_frame.setStyleSheet(
            f"background:{SURFACE}; border-radius:6px; border:1px solid {BORDER};"
        )
        df = QHBoxLayout(daily_frame)
        df.setContentsMargins(12, 8, 12, 8)
        df.addWidget(QLabel("Daily cost:"))
        self.daily_lbl = QLabel("$4.50")
        self.daily_lbl.setFont(font(13, bold=True))
        self.daily_lbl.setStyleSheet(f"color:{WARNING};")
        df.addStretch()
        df.addWidget(self.daily_lbl)
        inf.addWidget(daily_frame)

        # Years slider
        inf.addWidget(QLabel("Years of use:"))
        yr_row = QHBoxLayout()
        self.yr_slider = QSlider(Qt.Orientation.Horizontal)
        self.yr_slider.setRange(1, 20)
        self.yr_slider.setValue(1)
        self.yr_val = QLabel("1 yr")
        self.yr_val.setFont(font(11, bold=True))
        self.yr_val.setStyleSheet(f"color:{ACCENT};")
        self.yr_val.setFixedWidth(36)
        yr_row.addWidget(self.yr_slider, 1)
        yr_row.addWidget(self.yr_val)
        inf.addLayout(yr_row)
        self.yr_slider.valueChanged.connect(self._update_costs)

        left.addWidget(input_frame)
        left.addStretch()
        main_row.addLayout(left)

        # Right: cost breakdown + equivalents
        right = QVBoxLayout()
        right.setSpacing(10)

        # Cost breakdown rows
        self.rows = {}
        for label in ["Weekly", "Monthly", "Yearly", "5 Years", "10 Years"]:
            row = CostRow(label)
            right.addWidget(row)
            self.rows[label] = row

        # What you could have bought
        equiv_header = QLabel("What you could have bought instead (yearly):")
        equiv_header.setFont(font(11, bold=True))
        equiv_header.setStyleSheet(f"color:{TEXT};")
        right.addWidget(equiv_header)

        self.equiv_scroll = QScrollArea()
        self.equiv_scroll.setWidgetResizable(True)
        self.equiv_scroll.setFixedHeight(140)
        self.equiv_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.equiv_container = QWidget()
        self.equiv_grid = QGridLayout(self.equiv_container)
        self.equiv_grid.setSpacing(8)
        self.equiv_grid.setContentsMargins(0, 0, 0, 0)
        self.equiv_scroll.setWidget(self.equiv_container)
        right.addWidget(self.equiv_scroll)

        main_row.addLayout(right, 1)
        root.addLayout(main_row, 1)

        # Big lifetime number
        lifetime_frame = QFrame()
        lifetime_frame.setStyleSheet(
            f"background:{SURFACE}; border:2px solid {ACCENT}; border-radius:8px;"
        )
        lf = QHBoxLayout(lifetime_frame)
        lf.setContentsMargins(20, 12, 20, 12)

        lf.addWidget(QLabel("Lifetime cost (until 65):"))
        self.lifetime_lbl = AnimatedNumber()
        self.lifetime_lbl.setFont(font(24, bold=True))
        self.lifetime_lbl.setStyleSheet(f"color:{ACCENT};")
        lf.addStretch()
        lf.addWidget(self.lifetime_lbl)
        root.addWidget(lifetime_frame)

    def _on_product_change(self, name: str):
        self._update_costs()

    def _on_units_change(self, value: int):
        self.units_val.setText(str(value))
        self._update_costs()

    def _update_costs(self):
        product_name = self.product_combo.currentText()
        product = PRODUCTS[product_name]
        units = self.units_slider.value()
        years = self.yr_slider.value()
        self.yr_val.setText(f"{years} yr{'s' if years > 1 else ''}")

        daily = product["daily_cost"] * units
        self._daily_cost = daily
        self.daily_lbl.setText(f"${daily:.2f}")

        weekly   = daily * 7
        monthly  = daily * 30.44
        yearly   = daily * 365.25
        five_yr  = yearly * 5
        ten_yr   = yearly * 10

        current_age = 16   # average teen start
        lifetime = daily * 365.25 * (65 - current_age)

        self.rows["Weekly"].update_value(weekly)
        self.rows["Monthly"].update_value(monthly)
        self.rows["Yearly"].update_value(yearly)
        self.rows["5 Years"].update_value(five_yr)
        self.rows["10 Years"].update_value(ten_yr)
        self.lifetime_lbl.set_value(lifetime)

        self._update_equivalents(yearly)

    def _update_equivalents(self, yearly_cost: float):
        # Clear existing
        for card in self._equiv_cards:
            card.deleteLater()
        self._equiv_cards = []
        while self.equiv_grid.count():
            item = self.equiv_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        col = 0
        row = 0
        delay = 0
        for eq in EQUIVALENTS:
            count = int(yearly_cost / eq["cost"])
            if count < 1:
                continue
            card = EquivCard(eq, count)
            self.equiv_grid.addWidget(card, row, col)
            card.show_animated(delay)
            self._equiv_cards.append(card)
            delay += 80
            col += 1
            if col >= 4:
                col = 0
                row += 1
