"""
addiction_simulator.py — Choice-based addiction progression timeline.
Shows how quickly nicotine dependency forms based on usage pattern.
"""

import math
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QScrollArea, QGraphicsOpacityEffect)
from modules.theme import (BG, SURFACE, CARD, ACCENT, ACCENT2, TEXT, TEXT_DIM,
                            WARNING, SUCCESS, BORDER, font, fade_in)

# ── Timeline data ──────────────────────────────────────────────────────────────

TIMELINES = {
    "once": [
        {"period": "Day 1",    "event": "First hit. Dizziness, mild rush. Curious.",
         "craving": 1, "mood": "curious", "cost": 5},
        {"period": "Week 2",   "event": "Tried it again at a party. Felt good again.",
         "craving": 2, "mood": "relaxed", "cost": 10},
        {"period": "Month 2",  "event": "Using a couple times a week. 'I can stop anytime.'",
         "craving": 3, "mood": "confident", "cost": 45},
        {"period": "Month 4",  "event": "Reaching for it when stressed or bored.",
         "craving": 5, "mood": "anxious", "cost": 120},
        {"period": "Month 6",  "event": "Daily use. Feeling irritable without it.",
         "craving": 7, "mood": "dependent", "cost": 280},
        {"period": "Year 1",   "event": "Tried to quit once. Failed after 3 days.",
         "craving": 8, "mood": "trapped", "cost": 650},
        {"period": "Year 2",   "event": "Fully addicted. Hiding use from parents.",
         "craving": 9, "mood": "ashamed", "cost": 1400},
    ],
    "occasional": [
        {"period": "Week 1",   "event": "Weekend use only. Social habit forming.",
         "craving": 2, "mood": "social", "cost": 15},
        {"period": "Month 1",  "event": "Now using 3-4 times a week. 'Just weekends' is gone.",
         "craving": 4, "mood": "rationalizing", "cost": 60},
        {"period": "Month 3",  "event": "Daily use starts. Morning cravings kick in.",
         "craving": 6, "mood": "anxious", "cost": 180},
        {"period": "Month 5",  "event": "Can't focus in school without it. Grades slipping.",
         "craving": 8, "mood": "dependent", "cost": 360},
        {"period": "Month 8",  "event": "First quit attempt. Lasted 1 day.",
         "craving": 9, "mood": "desperate", "cost": 560},
        {"period": "Year 1",   "event": "Doctor notices early lung changes at checkup.",
         "craving": 9, "mood": "scared", "cost": 900},
    ],
    "daily": [
        {"period": "Week 1",   "event": "Daily use from day one. Feels normal quickly.",
         "craving": 3, "mood": "normalized", "cost": 20},
        {"period": "Week 3",   "event": "Morning craving before anything else.",
         "craving": 6, "mood": "dependent", "cost": 70},
        {"period": "Month 2",  "event": "Physical withdrawal symptoms between uses.",
         "craving": 8, "mood": "physical withdrawal", "cost": 160},
        {"period": "Month 4",  "event": "Using more to get the same effect. Tolerance built.",
         "craving": 9, "mood": "tolerant", "cost": 380},
        {"period": "Month 6",  "event": "Spending $200+/month. Lying about it.",
         "craving": 10, "mood": "compulsive", "cost": 680},
        {"period": "Year 1",   "event": "Tried to quit twice. Severe anxiety each time.",
         "craving": 10, "mood": "trapped", "cost": 1300},
    ],
}

MOOD_COLORS = {
    "curious":            "#4488ff",
    "relaxed":            "#44aa88",
    "confident":          "#44aa88",
    "social":             "#88aaff",
    "rationalizing":      "#ffaa44",
    "anxious":            "#ff8844",
    "dependent":          "#ff5533",
    "physical withdrawal":"#ff3322",
    "tolerant":           "#cc2200",
    "compulsive":         "#cc0000",
    "desperate":          "#cc0000",
    "scared":             "#ff4400",
    "trapped":            "#aa0000",
    "ashamed":            "#882200",
    "normalized":         "#ffaa44",
}

NOTIFICATION_MESSAGES = [
    "💭  \"I just need one to calm down.\"",
    "⚠   Morning fog lifts only after a hit.",
    "💸  Another $15 gone. Third time this week.",
    "😰  Hands shaking. Haven't had one in 6 hours.",
    "🧠  Can't concentrate. Brain keeps pulling toward it.",
    "📱  Sneaking out between classes to vape.",
    "😔  Friends noticed. You got defensive.",
    "🔄  You promised yourself this was the last one. Again.",
]


# ── Craving bar widget ─────────────────────────────────────────────────────────

class CravingBar(QWidget):
    def __init__(self, level: int):
        super().__init__()
        self._level = level
        self.setFixedSize(120, 14)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(SURFACE))
        p.drawRoundedRect(0, 0, w, h, 7, 7)
        filled = int(w * self._level / 10)
        t = self._level / 10.0
        bar_color = QColor(
            int(50 + t * 200),
            int(180 - t * 170),
            40,
        )
        if filled > 0:
            p.setBrush(bar_color)
            p.drawRoundedRect(0, 0, filled, h, 7, 7)
        p.end()


# ── Timeline node card ─────────────────────────────────────────────────────────

class TimelineNode(QFrame):
    def __init__(self, data: dict, index: int):
        super().__init__()
        self.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:8px;"
        )
        self.setFixedWidth(200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        period_lbl = QLabel(data["period"])
        period_lbl.setFont(font(10, bold=True))
        period_lbl.setStyleSheet(f"color:{ACCENT};")
        layout.addWidget(period_lbl)

        event_lbl = QLabel(data["event"])
        event_lbl.setFont(font(9))
        event_lbl.setWordWrap(True)
        event_lbl.setStyleSheet(f"color:{TEXT};")
        layout.addWidget(event_lbl)

        mood_color = MOOD_COLORS.get(data["mood"], TEXT_DIM)
        mood_lbl = QLabel(f"State: {data['mood']}")
        mood_lbl.setFont(font(9, italic=True))
        mood_lbl.setStyleSheet(f"color:{mood_color};")
        layout.addWidget(mood_lbl)

        craving_row = QHBoxLayout()
        cr_lbl = QLabel("Craving:")
        cr_lbl.setFont(font(9))
        cr_lbl.setStyleSheet(f"color:{TEXT_DIM};")
        craving_row.addWidget(cr_lbl)
        bar = CravingBar(data["craving"])
        craving_row.addWidget(bar)
        craving_row.addStretch()
        layout.addLayout(craving_row)

        cost_lbl = QLabel(f"Total spent: ${data['cost']}")
        cost_lbl.setFont(font(9, bold=True))
        cost_lbl.setStyleSheet(f"color:{WARNING};")
        layout.addWidget(cost_lbl)

        # Start hidden, fade in when revealed
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        self._effect = effect
        self._anim = None

    def reveal(self, delay_ms: int = 0):
        def start():
            self._anim = QPropertyAnimation(self._effect, b"opacity", self)
            self._anim.setDuration(500)
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self._anim.start()
        if delay_ms > 0:
            QTimer.singleShot(delay_ms, start)
        else:
            start()


# ── Notification popup (floating label) ───────────────────────────────────────

class NotificationPopup(QLabel):
    def __init__(self, text: str, parent: QWidget):
        super().__init__(text, parent)
        self.setFont(font(10))
        self.setStyleSheet(
            f"background:{SURFACE}; color:{WARNING}; border:1px solid {ACCENT};"
            f" border-radius:6px; padding:8px 14px;"
        )
        self.setWordWrap(True)
        self.adjustSize()
        self.raise_()

        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)

        self._fade_in = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_in.setDuration(400)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_in.start()

        QTimer.singleShot(3000, self._fade_out_and_hide)

    def _fade_out_and_hide(self):
        self._fade_out = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_out.setDuration(600)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_out.finished.connect(self.deleteLater)
        self._fade_out.start()


# ── Main AddictionSimulator screen ────────────────────────────────────────────

class AddictionSimulator(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._timeline_nodes = []
        self._notif_index = 0
        self._notif_timer = QTimer(self)
        self._notif_timer.timeout.connect(self._show_notification)
        self._build_ui()
        fade_in(self)

    def _build_ui(self):
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(24, 16, 24, 16)
        self.root.setSpacing(12)

        # Back + title
        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("back_btn")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(lambda: self.main_window.go_to_screen("nav"))
        top.addWidget(back_btn)
        top.addStretch()
        title = QLabel("How Fast Does It Happen?")
        title.setFont(font(18, bold=True))
        top.addWidget(title)
        top.addStretch()
        self.root.addLayout(top)

        subtitle = QLabel("Choose a starting scenario to see how addiction progresses.")
        subtitle.setFont(font(11))
        subtitle.setStyleSheet(f"color:{TEXT_DIM};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root.addWidget(subtitle)

        # Choice buttons
        self.choice_frame = QFrame()
        cf = QHBoxLayout(self.choice_frame)
        cf.setSpacing(16)
        cf.setContentsMargins(0, 8, 0, 8)

        scenarios = [
            ("try_once",    "Try Once",       "One-time curiosity at a party"),
            ("occasional",  "Occasional Use", "Weekends only, social situations"),
            ("daily",       "Daily Use",      "Regular use from the start"),
        ]
        self._choice_btns = {}
        for key, label, desc in scenarios:
            btn_frame = QFrame()
            btn_frame.setStyleSheet(
                f"background:{CARD}; border:1px solid {BORDER}; border-radius:8px;"
            )
            bf = QVBoxLayout(btn_frame)
            bf.setContentsMargins(16, 12, 16, 12)
            btn = QPushButton(label)
            btn.setFixedHeight(40)
            desc_lbl = QLabel(desc)
            desc_lbl.setFont(font(9))
            desc_lbl.setStyleSheet(f"color:{TEXT_DIM};")
            desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bf.addWidget(btn)
            bf.addWidget(desc_lbl)
            cf.addWidget(btn_frame, 1)
            tl_key = "once" if key == "try_once" else key
            btn.clicked.connect(lambda checked, k=tl_key: self._start_timeline(k))
            self._choice_btns[key] = btn

        self.root.addWidget(self.choice_frame)

        # Timeline scroll area (hidden until choice made)
        self.timeline_area = QScrollArea()
        self.timeline_area.setWidgetResizable(True)
        self.timeline_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timeline_area.setVisible(False)
        self.timeline_area.setFixedHeight(260)

        self.timeline_container = QWidget()
        self.timeline_layout = QHBoxLayout(self.timeline_container)
        self.timeline_layout.setContentsMargins(16, 8, 16, 8)
        self.timeline_layout.setSpacing(0)
        self.timeline_area.setWidget(self.timeline_container)
        self.root.addWidget(self.timeline_area)

        # End result panel (hidden until timeline complete)
        self.result_frame = QFrame()
        self.result_frame.setStyleSheet(
            f"background:{CARD}; border:1px solid {ACCENT}; border-radius:8px;"
        )
        self.result_frame.setVisible(False)
        rf = QHBoxLayout(self.result_frame)
        rf.setContentsMargins(20, 14, 20, 14)
        rf.setSpacing(30)

        self.result_cost_lbl = QLabel()
        self.result_cost_lbl.setFont(font(22, bold=True))
        self.result_cost_lbl.setStyleSheet(f"color:{WARNING};")
        rf.addWidget(self.result_cost_lbl)

        self.result_severity_lbl = QLabel()
        self.result_severity_lbl.setFont(font(14, bold=True))
        self.result_severity_lbl.setStyleSheet(f"color:{ACCENT};")
        rf.addWidget(self.result_severity_lbl)

        self.result_text_lbl = QLabel()
        self.result_text_lbl.setFont(font(10))
        self.result_text_lbl.setStyleSheet(f"color:{TEXT_DIM};")
        self.result_text_lbl.setWordWrap(True)
        rf.addWidget(self.result_text_lbl, 1)

        restart_btn = QPushButton("Try Another Path")
        restart_btn.setObjectName("secondary")
        restart_btn.clicked.connect(self._reset)
        rf.addWidget(restart_btn)

        self.root.addWidget(self.result_frame)
        self.root.addStretch()

    def _start_timeline(self, key: str):
        self._reset_timeline()
        self.timeline_area.setVisible(True)
        self.result_frame.setVisible(False)

        nodes_data = TIMELINES[key]
        self._timeline_nodes = []
        self._current_tl_key = key

        for i, data in enumerate(nodes_data):
            # Connector line
            if i > 0:
                connector = QWidget()
                connector.setFixedSize(30, 8)
                connector.setStyleSheet(f"background:{ACCENT}; border-radius:4px;")
                self.timeline_layout.addWidget(connector,
                                               alignment=Qt.AlignmentFlag.AlignVCenter)

            node = TimelineNode(data, i)
            self.timeline_layout.addWidget(node)
            self._timeline_nodes.append(node)
            node.reveal(delay_ms=i * 700)

        self.timeline_layout.addStretch()

        # Show result after all nodes revealed
        total_ms = len(nodes_data) * 700 + 800
        QTimer.singleShot(total_ms, lambda: self._show_result(nodes_data))

        # Start notifications
        self._notif_index = 0
        self._notif_timer.start(1800)

    def _show_notification(self):
        if self._notif_index >= len(NOTIFICATION_MESSAGES):
            self._notif_timer.stop()
            return
        msg = NOTIFICATION_MESSAGES[self._notif_index]
        self._notif_index += 1
        popup = NotificationPopup(msg, self)
        popup.setMaximumWidth(300)
        popup.adjustSize()
        # Position in bottom-right of this widget
        x = self.width() - popup.width() - 20
        y = self.height() - popup.height() - 60 - (self._notif_index % 3) * 50
        popup.move(max(0, x), max(0, y))
        popup.show()

    def _show_result(self, nodes_data: list):
        self.result_frame.setVisible(True)
        last = nodes_data[-1]
        total_cost = last["cost"]
        craving = last["craving"]
        severity = "MILD" if craving <= 3 else "MODERATE" if craving <= 6 else "SEVERE" if craving <= 8 else "CRITICAL"
        sev_color = SUCCESS if craving <= 3 else WARNING if craving <= 6 else ACCENT2 if craving <= 8 else ACCENT
        self.result_cost_lbl.setText(f"${total_cost:,} spent")
        self.result_severity_lbl.setText(f"Addiction: {severity}")
        self.result_severity_lbl.setStyleSheet(f"color:{sev_color}; font-size:14px; font-weight:bold;")

        messages = {
            "MILD":     "Early stage. Quitting now is much easier — success rates above 60%.",
            "MODERATE": "Habit is forming. Quitting takes effort but is very achievable with support.",
            "SEVERE":   "Strong dependency. Professional cessation support is recommended.",
            "CRITICAL": "Full addiction. Most people fail 8-11 quit attempts before succeeding.",
        }
        self.result_text_lbl.setText(messages[severity])
        fade_in(self.result_frame)

    def _reset_timeline(self):
        # Clear existing nodes
        for node in self._timeline_nodes:
            node.deleteLater()
        self._timeline_nodes = []
        # Remove all items from layout
        while self.timeline_layout.count():
            item = self.timeline_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._notif_timer.stop()

    def _reset(self):
        self._reset_timeline()
        self.timeline_area.setVisible(False)
        self.result_frame.setVisible(False)
