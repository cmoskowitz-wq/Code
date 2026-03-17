"""
stories.py — Teen story cards with timeline expansion and optional graphic mode.
"""

import json
import os
import math
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF
from PyQt6.QtGui import (QPainter, QColor, QPen, QBrush, QLinearGradient,
                          QFont, QRadialGradient)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QScrollArea, QFrame, QGridLayout,
                              QCheckBox, QSizePolicy, QGraphicsOpacityEffect,
                              QSpacerItem)
import modules.theme as T


def _load_stories():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "assets", "data", "stories.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class MedicalScanWidget(QWidget):
    """Draws a simulated medical scan using QPainter — no external images."""

    def __init__(self, description: str, parent=None):
        super().__init__(parent)
        self._description = description
        self._animated_offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)
        self.setMinimumHeight(160)
        self.setMinimumWidth(260)

    def _tick(self):
        self._animated_offset = (self._animated_offset + 0.05) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background: scan-like dark teal-grey
        p.fillRect(0, 0, w, h, QColor(12, 18, 22))

        # Scan grid lines
        grid_pen = QPen(QColor(30, 60, 60, 80))
        grid_pen.setWidth(1)
        p.setPen(grid_pen)
        step = 20
        for x in range(0, w, step):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            p.drawLine(0, y, w, y)

        # Central "organ" blob — irregular shape with spots
        cx, cy = w // 2, h // 2 - 10
        rx, ry = int(w * 0.30), int(h * 0.32)

        # Damaged tissue: dark brownish-red with irregular edges
        for i in range(8):
            angle = i * (math.pi * 2 / 8) + self._animated_offset * 0.1
            ex = cx + int(rx * (0.85 + 0.15 * math.sin(angle * 3 + 1.2)))
            ey = cy + int(ry * (0.85 + 0.15 * math.cos(angle * 2 + 0.8)))
            if i == 0:
                p.setPen(Qt.PenStyle.NoPen)
                grad = QRadialGradient(cx, cy, max(rx, ry))
                grad.setColorAt(0.0, QColor(90, 30, 20, 220))
                grad.setColorAt(0.6, QColor(60, 18, 12, 200))
                grad.setColorAt(1.0, QColor(30, 8, 5, 0))
                p.setBrush(QBrush(grad))
                p.drawEllipse(cx - rx, cy - ry, rx * 2, ry * 2)

        # Dark spots (tissue damage indicators)
        p.setPen(Qt.PenStyle.NoPen)
        spots = [
            (0.35, 0.40, 12, 8),
            (0.60, 0.45, 9, 7),
            (0.45, 0.60, 14, 10),
            (0.55, 0.35, 8, 6),
            (0.40, 0.52, 10, 8),
            (0.62, 0.58, 11, 9),
        ]
        for fx, fy, rw, rh in spots:
            sx = cx - rx + int(rx * 2 * fx)
            sy = cy - ry + int(ry * 2 * fy)
            p.setBrush(QColor(20, 8, 6, 200))
            p.drawEllipse(sx - rw, sy - rh, rw * 2, rh * 2)

        # Scan overlay lines (moving)
        scan_y = int((math.sin(self._animated_offset) * 0.5 + 0.5) * h)
        scan_pen = QPen(QColor(0, 200, 180, 60))
        scan_pen.setWidth(2)
        p.setPen(scan_pen)
        p.drawLine(0, scan_y, w, scan_y)

        # Red corner markers (scan frame)
        corner_pen = QPen(QColor(204, 0, 0, 180))
        corner_pen.setWidth(2)
        p.setPen(corner_pen)
        m, sz = 8, 16
        for cx2, cy2, dx, dy in [(m, m, 1, 1), (w - m, m, -1, 1),
                                   (m, h - m, 1, -1), (w - m, h - m, -1, -1)]:
            p.drawLine(cx2, cy2, cx2 + dx * sz, cy2)
            p.drawLine(cx2, cy2, cx2, cy2 + dy * sz)

        # Description text at bottom
        text_bg = QColor(0, 0, 0, 160)
        p.fillRect(0, h - 38, w, 38, text_bg)
        p.setPen(QColor(180, 180, 180))
        p.setFont(T.font(8))
        p.drawText(QRectF(6, h - 36, w - 12, 34),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   self._description[:120])


class GraphicPlaceholder(QWidget):
    """Grey placeholder shown when graphic mode is OFF."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(140)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(40, 40, 40))
        p.setPen(QColor(80, 80, 80))
        p.drawRect(1, 1, w - 2, h - 2)
        p.setFont(T.font(11))
        p.setPen(QColor(100, 100, 100))
        p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter,
                   "[ Enable graphic content to view medical imagery ]")


class TimelineWidget(QWidget):
    """Horizontal scrolling timeline of story events."""

    def __init__(self, events: list, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(0)

        for i, ev in enumerate(events):
            node = QWidget()
            node_layout = QVBoxLayout(node)
            node_layout.setContentsMargins(8, 4, 8, 4)
            node_layout.setSpacing(4)

            dot_label = QLabel("●")
            dot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot_label.setStyleSheet(f"color: {T.ACCENT}; font-size: 14px; background: transparent;")
            node_layout.addWidget(dot_label)

            time_lbl = QLabel(ev.get("offset", ""))
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            time_lbl.setFont(T.font(9, bold=True))
            time_lbl.setStyleSheet(f"color: {T.ACCENT2}; background: transparent;")
            node_layout.addWidget(time_lbl)

            event_lbl = QLabel(ev.get("event", ""))
            event_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            event_lbl.setWordWrap(True)
            event_lbl.setFont(T.font(9))
            event_lbl.setStyleSheet(f"color: {T.TEXT_DIM}; background: transparent;")
            event_lbl.setMaximumWidth(140)
            node_layout.addWidget(event_lbl)

            layout.addWidget(node)

            # Connector line
            if i < len(events) - 1:
                line = QLabel("──────")
                line.setAlignment(Qt.AlignmentFlag.AlignCenter)
                line.setStyleSheet(f"color: {T.BORDER}; background: transparent; font-size: 10px;")
                layout.addWidget(line)

        layout.addStretch()


class StoryCard(QFrame):
    """A collapsible story card."""

    def __init__(self, story: dict, graphic_enabled_ref: list, parent=None):
        super().__init__(parent)
        self._story = story
        self._graphic_ref = graphic_enabled_ref  # mutable reference [bool]
        self._expanded = False
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {T.CARD};
                border: 1px solid {T.BORDER};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {T.ACCENT};
            }}
        """)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(20, 16, 20, 16)
        self._main_layout.setSpacing(10)

        # Header row
        header = QHBoxLayout()
        name_age = QLabel(f"{self._story['name']}, {self._story['age']}")
        name_age.setFont(T.font(15, bold=True))
        name_age.setStyleSheet(f"color: {T.TEXT}; background: transparent;")
        header.addWidget(name_age)
        header.addStretch()

        self._toggle_btn = QPushButton("Read Story ▼")
        self._toggle_btn.setObjectName("secondary")
        self._toggle_btn.setFixedSize(130, 32)
        self._toggle_btn.setFont(T.font(10))
        self._toggle_btn.clicked.connect(self._toggle)
        header.addWidget(self._toggle_btn)
        self._main_layout.addLayout(header)

        # Summary
        summary = QLabel(self._story['summary'])
        summary.setFont(T.font(12))
        summary.setStyleSheet(f"color: {T.TEXT_DIM}; background: transparent;")
        summary.setWordWrap(True)
        self._main_layout.addWidget(summary)

        # Expandable section
        self._expanded_widget = QWidget()
        self._expanded_widget.setStyleSheet("background: transparent;")
        exp_layout = QVBoxLayout(self._expanded_widget)
        exp_layout.setContentsMargins(0, 8, 0, 0)
        exp_layout.setSpacing(14)

        # Full story
        full = QLabel(self._story['full_story'])
        full.setFont(T.font(12))
        full.setStyleSheet(f"color: {T.TEXT_DIM}; background: transparent;")
        full.setWordWrap(True)
        exp_layout.addWidget(full)

        # Timeline
        timeline_title = QLabel("Timeline")
        timeline_title.setFont(T.font(11, bold=True))
        timeline_title.setStyleSheet(f"color: {T.ACCENT2}; background: transparent;")
        exp_layout.addWidget(timeline_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(110)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        tl = TimelineWidget(self._story.get('timeline', []))
        scroll.setWidget(tl)
        exp_layout.addWidget(scroll)

        # Quote
        quote_label = QLabel(f'"{self._story["quote"]}"')
        quote_label.setFont(T.font(12, italic=True))
        quote_label.setStyleSheet(f"""
            color: {T.TEXT};
            background-color: #111;
            border-left: 3px solid {T.ACCENT};
            padding: 10px 14px;
            border-radius: 0px;
        """)
        quote_label.setWordWrap(True)
        exp_layout.addWidget(quote_label)

        # Medical image section
        img_title = QLabel("Medical Documentation")
        img_title.setFont(T.font(11, bold=True))
        img_title.setStyleSheet(f"color: {T.WARNING}; background: transparent;")
        exp_layout.addWidget(img_title)

        self._placeholder = GraphicPlaceholder()
        self._scan_widget = MedicalScanWidget(self._story.get('graphic_description', ''))
        exp_layout.addWidget(self._placeholder)
        exp_layout.addWidget(self._scan_widget)
        self._scan_widget.hide()

        self._expanded_widget.hide()
        self._main_layout.addWidget(self._expanded_widget)

    def _toggle(self):
        self._expanded = not self._expanded
        if self._expanded:
            self._expanded_widget.show()
            self._toggle_btn.setText("Close ▲")
            self._update_graphic_mode()
        else:
            self._expanded_widget.hide()
            self._toggle_btn.setText("Read Story ▼")

    def refresh_graphic_mode(self):
        if self._expanded:
            self._update_graphic_mode()

    def _update_graphic_mode(self):
        if self._graphic_ref[0]:
            self._placeholder.hide()
            self._scan_widget.show()
        else:
            self._scan_widget.hide()
            self._placeholder.show()


class StoriesScreen(QWidget):
    def __init__(self, nav_callback, parent=None):
        super().__init__(parent)
        self._nav = nav_callback
        self._graphic_enabled = [False]  # mutable reference passed to cards
        self._cards = []
        self._setup_ui()
        self._load_stories()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
        top_bar = QWidget()
        top_bar.setFixedHeight(56)
        top_bar.setStyleSheet(f"background-color: {T.SURFACE}; border-bottom: 1px solid {T.BORDER};")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 0, 24, 0)

        back_btn = QPushButton("← Back")
        back_btn.setObjectName("back_btn")
        back_btn.setFixedSize(90, 34)
        back_btn.clicked.connect(lambda: self._nav("nav_hub"))
        top_layout.addWidget(back_btn)

        title = QLabel("Real Stories")
        title.setFont(T.font(16, bold=True))
        title.setStyleSheet(f"color: {T.TEXT}; background: transparent;")
        top_layout.addWidget(title)
        top_layout.addStretch()

        self._graphic_toggle = QCheckBox("Show Medical Content")
        self._graphic_toggle.setStyleSheet(f"""
            QCheckBox {{ color: {T.WARNING}; background: transparent; font-size: 12px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; }}
            QCheckBox::indicator:unchecked {{ background: {T.SURFACE}; border: 1px solid {T.BORDER}; border-radius: 3px; }}
            QCheckBox::indicator:checked {{ background: {T.ACCENT}; border: 1px solid {T.ACCENT}; border-radius: 3px; }}
        """)
        self._graphic_toggle.stateChanged.connect(self._on_graphic_toggle)
        top_layout.addWidget(self._graphic_toggle)

        root.addWidget(top_bar)

        # Subtitle
        subtitle_bar = QWidget()
        subtitle_bar.setStyleSheet(f"background-color: {T.BG};")
        sb_layout = QHBoxLayout(subtitle_bar)
        sb_layout.setContentsMargins(32, 16, 32, 8)
        subtitle = QLabel("Five fictional but clinically realistic accounts of teen nicotine dependency.")
        subtitle.setFont(T.font(12))
        subtitle.setStyleSheet(f"color: {T.TEXT_DIM}; background: transparent;")
        sb_layout.addWidget(subtitle)
        root.addWidget(subtitle_bar)

        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self._card_container = QWidget()
        self._card_container.setStyleSheet(f"background-color: {T.BG};")
        self._cards_layout = QVBoxLayout(self._card_container)
        self._cards_layout.setContentsMargins(32, 8, 32, 32)
        self._cards_layout.setSpacing(16)

        scroll.setWidget(self._card_container)
        root.addWidget(scroll, 1)

    def _load_stories(self):
        try:
            stories = _load_stories()
        except Exception as e:
            err = QLabel(f"Could not load stories: {e}")
            err.setStyleSheet(f"color: {T.ACCENT}; background: transparent;")
            self._cards_layout.addWidget(err)
            return

        for story in stories:
            card = StoryCard(story, self._graphic_enabled)
            self._cards.append(card)
            self._cards_layout.addWidget(card)

        self._cards_layout.addStretch()

    def _on_graphic_toggle(self, state):
        self._graphic_enabled[0] = bool(state)
        for card in self._cards:
            card.refresh_graphic_mode()
