"""
personal_impact.py — Personalized health and financial impact report.
User enters age and use status, receives a projected impact timeline.
"""

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QSlider, QComboBox,
                              QLineEdit, QScrollArea, QStackedWidget,
                              QGraphicsOpacityEffect, QSizePolicy)
from modules.theme import (BG, SURFACE, CARD, ACCENT, ACCENT2, TEXT, TEXT_DIM,
                            WARNING, SUCCESS, BORDER, font, fade_in)

USE_STATUSES = [
    "Never used nicotine",
    "Tried it once or twice",
    "Occasional user (weekends)",
    "Daily user",
    "Trying to quit",
]

# ── Timeline bar widget ────────────────────────────────────────────────────────

class TimelineBar(QWidget):
    """Horizontal bar showing health trajectory over years."""
    def __init__(self, events: list):
        super().__init__()
        self._events = events
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(SURFACE))

        if not self._events:
            p.end()
            return

        line_y = 36
        p.setPen(QPen(QColor(BORDER), 2))
        p.drawLine(20, line_y, w - 20, line_y)

        step = (w - 40) / max(len(self._events) - 1, 1)

        for i, ev in enumerate(self._events):
            x = int(20 + i * step)
            color = QColor(ev.get("color", ACCENT))

            # Dot
            p.setPen(QPen(color, 2))
            p.setBrush(color)
            p.drawEllipse(x - 6, line_y - 6, 12, 12)

            # Year label above
            p.setPen(color)
            p.setFont(font(8, bold=True))
            p.drawText(x - 25, 4, 50, 18,
                       Qt.AlignmentFlag.AlignCenter, ev.get("year_label", ""))

            # Event label below
            p.setPen(QColor(TEXT_DIM))
            p.setFont(font(8))
            text = ev.get("label", "")
            p.drawText(x - 45, line_y + 12, 90, 36,
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                       text)

        p.end()


# ── Stat card ─────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    def __init__(self, label: str, value: str, sublabel: str = "", color: str = WARNING):
        super().__init__()
        self.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:8px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        val_lbl = QLabel(value)
        val_lbl.setFont(font(22, bold=True))
        val_lbl.setStyleSheet(f"color:{color};")
        layout.addWidget(val_lbl)

        lbl = QLabel(label)
        lbl.setFont(font(10, bold=True))
        layout.addWidget(lbl)

        if sublabel:
            sub = QLabel(sublabel)
            sub.setFont(font(9))
            sub.setStyleSheet(f"color:{TEXT_DIM};")
            sub.setWordWrap(True)
            layout.addWidget(sub)


# ── Report page ───────────────────────────────────────────────────────────────

class ReportPage(QWidget):
    def __init__(self, profile: dict):
        super().__init__()
        age = profile["age"]
        status = profile["status"]
        name = profile.get("name", "").strip() or "You"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header
        header_color = SUCCESS if "Never" in status else (WARNING if "quit" in status.lower() else ACCENT)
        header = QLabel(f"Personal Impact Report — {name}, Age {age}")
        header.setFont(font(15, bold=True))
        header.setStyleSheet(f"color:{header_color};")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Status-specific message
        status_msgs = {
            "Never used nicotine": (
                "You are nicotine-free. This report shows what you're avoiding by staying that way.",
                SUCCESS,
            ),
            "Tried it once or twice": (
                "Early stage. Your brain hasn't rewired yet. Every day clean makes quitting easier.",
                WARNING,
            ),
            "Occasional user (weekends)": (
                "Weekend use isn't safe — adolescent brains form dependencies 4× faster than adults.",
                WARNING,
            ),
            "Daily user": (
                "Daily use at your age causes measurable brain changes in 3-6 months. The clock is running.",
                ACCENT,
            ),
            "Trying to quit": (
                "Quitting is the best decision you'll ever make. Most people need multiple attempts — that's normal.",
                SUCCESS,
            ),
        }
        msg_text, msg_color = status_msgs.get(status, ("", TEXT_DIM))
        msg_lbl = QLabel(msg_text)
        msg_lbl.setFont(font(11))
        msg_lbl.setStyleSheet(
            f"color:{msg_color}; background:{SURFACE}; border-radius:6px; padding:10px;"
        )
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg_lbl)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 8, 0)
        cl.setSpacing(14)

        # Stat cards row
        years_to_65 = max(0, 65 - age)
        is_user = status not in ("Never used nicotine",)
        daily_cost = 4.50 if is_user else 0
        lifetime_cost = daily_cost * 365 * years_to_65

        card_row = QHBoxLayout()
        card_row.setSpacing(10)

        if is_user:
            card_row.addWidget(StatCard(
                "Lifetime cost if you continue",
                f"${lifetime_cost:,.0f}",
                f"${daily_cost:.2f}/day × {years_to_65} years to age 65",
                WARNING,
            ))
            card_row.addWidget(StatCard(
                "Years of exposure risk",
                f"{years_to_65}",
                "Years of continued lung/heart/brain damage",
                ACCENT,
            ))
            quit_success = "6%" if age > 25 else "23%"
            card_row.addWidget(StatCard(
                "First-attempt quit success rate",
                quit_success,
                "Most people require 8-11 attempts. Professional support triples success.",
                WARNING,
            ))
        else:
            card_row.addWidget(StatCard(
                "Money you'll save (to age 65)",
                f"${daily_cost * 365 * years_to_65:,.0f}",
                "Compared to average daily user",
                SUCCESS,
            ))
            card_row.addWidget(StatCard(
                "Lung cancer risk reduction",
                "~85%",
                "Compared to lifetime smoker",
                SUCCESS,
            ))
            card_row.addWidget(StatCard(
                "Expected healthy life years",
                f"+{min(10, years_to_65 // 5)}",
                "Compared to a 20-year smoker",
                SUCCESS,
            ))

        cl.addLayout(card_row)

        # Health timeline
        cl.addWidget(QLabel("Your Health Projection Timeline:") )
        tl_label = cl.itemAt(cl.count() - 1).widget()
        tl_label.setFont(font(11, bold=True))

        events = self._build_timeline(age, status)
        tl = TimelineBar(events)
        cl.addWidget(tl)

        # Key risks / benefits
        if is_user:
            section_title = "Health Risks at Your Age:"
            points = self._user_risks(age)
            pt_color = ACCENT
        else:
            section_title = "Why Staying Nicotine-Free Matters at Your Age:"
            points = self._non_user_benefits(age)
            pt_color = SUCCESS

        cl.addWidget(self._make_bullet_section(section_title, points, pt_color))

        # If quitting section for users
        if "quit" in status.lower() or is_user:
            cl.addWidget(self._make_quit_section(age))

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

    def _build_timeline(self, age: int, status: str) -> list:
        is_user = status not in ("Never used nicotine",)
        events = []

        if is_user:
            events.append({"year_label": f"Age {age}", "label": "Now\n(current use)", "color": WARNING})
            if age + 1 <= 25:
                events.append({"year_label": f"Age {age+1}", "label": "Dependency\nsolidifies", "color": "#ff8800"})
            if age + 3 <= 40:
                events.append({"year_label": f"Age {age+3}", "label": "Lung capacity\nnoticeably reduced", "color": ACCENT})
            if age + 10 <= 55:
                events.append({"year_label": f"Age {age+10}", "label": "COPD risk\nbecomes real", "color": ACCENT})
            events.append({"year_label": "Age 65", "label": "Retirement\nwith disease burden", "color": "#880000"})
        else:
            events.append({"year_label": f"Age {age}", "label": "Now\n(nicotine-free)", "color": SUCCESS})
            events.append({"year_label": f"Age {age+5}", "label": "Full lung\ndevelopment", "color": SUCCESS})
            events.append({"year_label": f"Age {age+15}", "label": "Peak\nfitness potential", "color": SUCCESS})
            events.append({"year_label": "Age 65", "label": "Retirement\nwith full health", "color": SUCCESS})

        return events

    def _user_risks(self, age: int) -> list:
        risks = [
            "Your lungs are still developing — damage before 21 is permanent.",
            "Nicotine rewires adolescent prefrontal cortex, impairing decision-making.",
            "Daily users at your age have 3× higher anxiety rates than non-users.",
        ]
        if age <= 16:
            risks.append("Under 16: brain plasticity is at its highest — and most vulnerable.")
        elif age <= 18:
            risks.append("You are 2-4× more likely to be addicted for life if you started before 18.")
        return risks

    def _non_user_benefits(self, age: int) -> list:
        return [
            "Your cardiovascular system is developing optimally without nicotine stress.",
            "Your dopamine system is intact — rewards feel real and motivating.",
            f"By staying clean until 21, you avoid 90% of lifetime addiction risk.",
            "Your athletic performance is significantly better than peers who vape.",
        ]

    def _make_bullet_section(self, title: str, points: list, color: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:8px;"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        t = QLabel(title)
        t.setFont(font(11, bold=True))
        layout.addWidget(t)

        for pt in points:
            row = QHBoxLayout()
            dot = QLabel("•")
            dot.setFont(font(12, bold=True))
            dot.setStyleSheet(f"color:{color};")
            dot.setFixedWidth(14)
            row.addWidget(dot)
            lbl = QLabel(pt)
            lbl.setFont(font(10))
            lbl.setStyleSheet(f"color:{TEXT_DIM};")
            lbl.setWordWrap(True)
            row.addWidget(lbl, 1)
            layout.addLayout(row)

        return frame

    def _make_quit_section(self, age: int) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"background:{SURFACE}; border:1px solid {SUCCESS}; border-radius:8px;"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        t = QLabel("If You Quit Today:")
        t.setFont(font(11, bold=True))
        t.setStyleSheet(f"color:{SUCCESS};")
        layout.addWidget(t)

        benefits = [
            ("20 minutes", "Heart rate and blood pressure drop"),
            ("12 hours", "CO levels in blood return to normal"),
            ("2–3 weeks", "Circulation improves, lung function increases"),
            ("1–9 months", "Coughing decreases, lung cilia regenerate"),
            ("1 year", "Heart attack risk halved"),
            ("5 years", "Stroke risk same as a non-smoker"),
            ("10 years", "Lung cancer risk halved"),
        ]

        for time, benefit in benefits:
            row = QHBoxLayout()
            time_lbl = QLabel(time)
            time_lbl.setFont(font(9, bold=True))
            time_lbl.setStyleSheet(f"color:{SUCCESS};")
            time_lbl.setFixedWidth(90)
            row.addWidget(time_lbl)
            b_lbl = QLabel(benefit)
            b_lbl.setFont(font(9))
            b_lbl.setStyleSheet(f"color:{TEXT_DIM};")
            row.addWidget(b_lbl, 1)
            layout.addLayout(row)

        return frame


# ── Loading animation ─────────────────────────────────────────────────────────

class LoadingWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        self._dots = 0
        self._lbl = QLabel("Calculating your personal impact...")
        self._lbl.setFont(font(14))
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(400)

    def _tick(self):
        self._dots = (self._dots + 1) % 4
        self._lbl.setText("Calculating your personal impact" + "." * self._dots)

    def stop(self):
        self._timer.stop()


# ── Main PersonalImpact screen ────────────────────────────────────────────────

class PersonalImpact(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._profile = {}
        self._stack = QStackedWidget(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._stack)

        self._form_page = self._build_form()
        self._loading_page = LoadingWidget()
        self._report_page = None

        self._stack.addWidget(self._form_page)
        self._stack.addWidget(self._loading_page)
        self._stack.setCurrentIndex(0)
        fade_in(self)

    def _build_form(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(14)

        # Back + title
        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("back_btn")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(lambda: self.main_window.go_to_screen("nav"))
        top.addWidget(back_btn)
        top.addStretch()
        title = QLabel("Your Personal Impact")
        title.setFont(font(18, bold=True))
        top.addWidget(title)
        top.addStretch()
        layout.addLayout(top)

        subtitle = QLabel("Answer a few quick questions to see your personalized nicotine impact report.")
        subtitle.setFont(font(11))
        subtitle.setStyleSheet(f"color:{TEXT_DIM};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        form = QFrame()
        form.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:10px;"
        )
        form.setMaximumWidth(500)
        fl = QVBoxLayout(form)
        fl.setContentsMargins(28, 24, 28, 24)
        fl.setSpacing(18)

        # Name (optional)
        fl.addWidget(self._field_label("First name (optional):"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Leave blank to stay anonymous")
        fl.addWidget(self.name_input)

        # Age
        fl.addWidget(self._field_label("Your age:"))
        age_row = QHBoxLayout()
        self.age_slider = QSlider(Qt.Orientation.Horizontal)
        self.age_slider.setRange(13, 25)
        self.age_slider.setValue(16)
        self.age_val = QLabel("16")
        self.age_val.setFont(font(12, bold=True))
        self.age_val.setStyleSheet(f"color:{ACCENT};")
        self.age_val.setFixedWidth(28)
        age_row.addWidget(self.age_slider, 1)
        age_row.addWidget(self.age_val)
        self.age_slider.valueChanged.connect(lambda v: self.age_val.setText(str(v)))
        fl.addLayout(age_row)

        # Use status
        fl.addWidget(self._field_label("Your current nicotine use:"))
        self.status_combo = QComboBox()
        for s in USE_STATUSES:
            self.status_combo.addItem(s)
        fl.addWidget(self.status_combo)

        submit_btn = QPushButton("Generate My Report →")
        submit_btn.setFixedHeight(46)
        submit_btn.clicked.connect(self._submit)
        fl.addWidget(submit_btn)

        layout.addWidget(form, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        return page

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(font(11))
        return lbl

    def _submit(self):
        self._profile = {
            "name":   self.name_input.text(),
            "age":    self.age_slider.value(),
            "status": self.status_combo.currentText(),
        }
        # Show loading briefly, then report
        self._stack.setCurrentIndex(1)
        QTimer.singleShot(1400, self._show_report)

    def _show_report(self):
        self._loading_page.stop()

        # Build report page wrapper with back button
        wrapper = QWidget()
        wl = QVBoxLayout(wrapper)
        wl.setContentsMargins(24, 16, 24, 16)
        wl.setSpacing(10)

        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("back_btn")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(self._go_back_to_form)
        top.addWidget(back_btn)
        top.addStretch()
        home_btn = QPushButton("Main Menu")
        home_btn.setObjectName("secondary")
        home_btn.setFixedWidth(110)
        home_btn.clicked.connect(lambda: self.main_window.go_to_screen("nav"))
        top.addWidget(home_btn)
        wl.addLayout(top)

        report = ReportPage(self._profile)
        wl.addWidget(report, 1)

        self._report_page = wrapper
        self._stack.addWidget(wrapper)
        self._stack.setCurrentWidget(wrapper)
        fade_in(wrapper)

    def _go_back_to_form(self):
        self._stack.setCurrentIndex(0)
        if self._report_page:
            self._report_page.deleteLater()
            self._report_page = None
