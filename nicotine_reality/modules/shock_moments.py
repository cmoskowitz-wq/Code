"""
shock_moments.py — Random shocking-stat popup overlays.
Appears every 60-120 seconds while the app is active (not on start screen).
"""

import random
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QGraphicsOpacityEffect, QFrame)
from modules.theme import (BG, SURFACE, CARD, ACCENT, ACCENT2, TEXT, TEXT_DIM,
                            WARNING, BORDER, font)

SHOCK_MESSAGES = [
    {
        "stat":   "Right now, nicotine is reshaping 600+ teen brains.",
        "detail": "Every hour, roughly 600 adolescents in the US take their first nicotine hit.",
    },
    {
        "stat":   "Most people who try to quit fail 8–11 times before succeeding.",
        "detail": "The average smoker makes 30+ quit attempts over their lifetime. Addiction is not a character flaw — it's neuroscience.",
    },
    {
        "stat":   "Teen vapers are 4× more likely to start smoking cigarettes.",
        "detail": "A 2019 National Academy of Sciences study confirmed vaping is a gateway to combustible tobacco for adolescents.",
    },
    {
        "stat":   "Nicotine permanently alters teen brain chemistry in as few as 30 days.",
        "detail": "Adolescent dopamine systems rewire around nicotine much faster than adult brains.",
    },
    {
        "stat":   "The vape industry spends $8.6 billion/year marketing to teens.",
        "detail": "Fruit flavors, influencer sponsorships, and social media tactics are deliberately designed to target those under 21.",
    },
    {
        "stat":   "1 in 5 high school students currently uses e-cigarettes.",
        "detail": "This is higher than the smoking rate was at any point in the past 20 years.",
    },
    {
        "stat":   "Nicotine withdrawal can cause depression severe enough to require medication.",
        "detail": "Quitting after heavy use produces anxiety, insomnia, and depression that can last weeks — not just cravings.",
    },
    {
        "stat":   "A single Juul pod contains as much nicotine as a full pack of cigarettes.",
        "detail": "Many teens vaping 'just a little' are actually consuming pack-a-day equivalent doses.",
    },
    {
        "stat":   "Second-hand vape aerosol contains 10+ toxic chemicals, including formaldehyde.",
        "detail": "Vaping is not just water vapor. The aerosol contains heavy metals, ultrafine particles, and volatile organic compounds.",
    },
    {
        "stat":   "Nicotine makes anxiety worse — not better — in the long run.",
        "detail": "It provides 20 minutes of relief by suppressing the very withdrawal it caused. Without it, anxiety is higher than baseline.",
    },
    {
        "stat":   "Smokers lose an average of 10 years of life expectancy.",
        "detail": "Half of all long-term smokers die of a smoking-related disease. That's not a statistic — it's every second person.",
    },
    {
        "stat":   "Nicotine during adolescence impairs learning and memory formation.",
        "detail": "The prefrontal cortex — responsible for studying, decision-making, and focus — doesn't fully develop until 25.",
    },
    {
        "stat":   "90% of adult smokers started before age 18.",
        "detail": "Almost no one becomes addicted as an adult. The window of vulnerability is your teen years.",
    },
    {
        "stat":   "E-cigarette companies were bought by tobacco giants after vaping surged.",
        "detail": "Altria (Marlboro) invested $12.8 billion in Juul. The goal is the same: a lifetime of addiction.",
    },
    {
        "stat":   "EVALI killed 68 people and hospitalized 2,800 in 2019–2020.",
        "detail": "E-cigarette or vaping product use–associated lung injury (EVALI) can appear within weeks of starting to vape.",
    },
]


class ShockPopup(QWidget):
    """Floating overlay popup that appears over the main window."""

    def __init__(self, message: dict, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(Qt.WindowType.Widget)

        # Semi-transparent dark overlay fill
        self._overlay_opacity = 0.65

        # Inner card
        self._card = QFrame(self)
        self._card.setStyleSheet(
            f"background:{SURFACE}; border:2px solid {ACCENT}; border-radius:10px;"
        )

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        icon_row = QHBoxLayout()
        icon = QLabel("⚠")
        icon.setFont(font(28))
        icon.setStyleSheet(f"color:{WARNING};")
        icon_row.addWidget(icon)
        icon_row.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(
            f"background:transparent; color:{TEXT_DIM}; border:none; font-size:14px;"
        )
        close_btn.clicked.connect(self._dismiss)
        icon_row.addWidget(close_btn)
        card_layout.addLayout(icon_row)

        stat_lbl = QLabel(message["stat"])
        stat_lbl.setFont(font(15, bold=True))
        stat_lbl.setStyleSheet(f"color:{ACCENT2};")
        stat_lbl.setWordWrap(True)
        card_layout.addWidget(stat_lbl)

        detail_lbl = QLabel(message["detail"])
        detail_lbl.setFont(font(10))
        detail_lbl.setStyleSheet(f"color:{TEXT_DIM};")
        detail_lbl.setWordWrap(True)
        card_layout.addWidget(detail_lbl)

        dismiss_btn = QPushButton("Got it — close")
        dismiss_btn.setObjectName("secondary")
        dismiss_btn.clicked.connect(self._dismiss)
        card_layout.addWidget(dismiss_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Opacity effect on self
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)

        self._fade_in = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_in.setDuration(400)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_in.start()

        # Auto-dismiss after 8 seconds
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._dismiss)
        self._auto_timer.start(8000)

    def showEvent(self, event):
        super().showEvent(event)
        self._reposition()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition()

    def _reposition(self):
        if self.parent():
            pw = self.parent().width()
            ph = self.parent().height()
        else:
            return
        self.setGeometry(0, 0, pw, ph)

        card_w = min(460, pw - 80)
        card_h = 260
        card_x = (pw - card_w) // 2
        card_y = (ph - card_h) // 2
        self._card.setGeometry(card_x, card_y, card_w, card_h)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(0, 0, self.width(), self.height(),
                   QColor(0, 0, 0, int(255 * self._overlay_opacity)))
        p.end()

    def _dismiss(self):
        self._auto_timer.stop()
        out = QPropertyAnimation(self._effect, b"opacity", self)
        out.setDuration(300)
        out.setStartValue(1.0)
        out.setEndValue(0.0)
        out.setEasingCurve(QEasingCurve.Type.InOutQuad)
        out.finished.connect(self.deleteLater)
        out.start()
        self._fade_out = out


class ShockMomentManager:
    """Manages the random shock moment timer and popup display."""

    def __init__(self, main_window: QWidget):
        self._window = main_window
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)
        self._used_indices: set = set()
        self._active = False

    def start(self):
        self._active = True
        self._schedule_next()

    def stop(self):
        self._active = False
        self._timer.stop()

    def _schedule_next(self):
        interval = random.randint(60_000, 120_000)   # 60-120 seconds
        self._timer.start(interval)

    def _fire(self):
        if not self._active:
            return

        # Don't show on start screen
        current = getattr(self._window, "_current_screen", None)
        if current in (None, "start"):
            self._schedule_next()
            return

        # Pick a message (avoid immediate repeats)
        available = [i for i in range(len(SHOCK_MESSAGES)) if i not in self._used_indices]
        if not available:
            self._used_indices.clear()
            available = list(range(len(SHOCK_MESSAGES)))

        idx = random.choice(available)
        self._used_indices.add(idx)
        if len(self._used_indices) > len(SHOCK_MESSAGES) // 2:
            self._used_indices.pop() if hasattr(self._used_indices, 'pop') else None
            oldest = min(self._used_indices)
            self._used_indices.discard(oldest)

        popup = ShockPopup(SHOCK_MESSAGES[idx], self._window)
        popup.show()
        popup._reposition()

        self._schedule_next()
