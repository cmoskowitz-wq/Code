"""
body_simulator.py — Interactive body organ damage visualizer.
Users select an organ and move sliders to see real-time damage progression.
All visuals are drawn with QPainter — no external image files required.
"""

import math
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF, QPointF
from PyQt6.QtGui import (QPainter, QColor, QPen, QBrush, QLinearGradient,
                         QRadialGradient, QPainterPath, QFont)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QSlider, QFrame, QSizePolicy)
from modules.theme import (BG, SURFACE, CARD, ACCENT, ACCENT2, TEXT, TEXT_DIM,
                            WARNING, BORDER, font, fade_in)


# ── Organ facts ────────────────────────────────────────────────────────────────
ORGAN_FACTS = {
    "lungs": [
        "Nicotine paralyzes cilia — the tiny hairs that sweep out toxins.",
        "After 20 cigarettes/day for 10 years, FEV1 can drop 30–40%.",
        "COPD develops silently; you often don't notice until 50% lung function is gone.",
        "Teen lungs are still growing — damage before 18 is permanent.",
    ],
    "brain": [
        "Nicotine triggers dopamine release 4× faster than natural rewards.",
        "After regular use, the brain reduces its own dopamine receptors.",
        "Adolescent brains are 2–4× more vulnerable to addiction than adult brains.",
        "Withdrawal can cause depression, anxiety, and cognitive fog for weeks.",
    ],
    "heart": [
        "Nicotine raises heart rate by 10–20 bpm within seconds of use.",
        "Carbon monoxide displaces oxygen in blood, straining the heart.",
        "Smokers are 2–4× more likely to develop coronary artery disease.",
        "Arteries lose elasticity — raising blood pressure permanently.",
    ],
}


# ── Individual organ painters ──────────────────────────────────────────────────

class LungsWidget(QWidget):
    """Animated lung capacity visualization."""

    def __init__(self):
        super().__init__()
        self._damage = 0.0          # 0.0 (healthy) → 1.0 (destroyed)
        self._breath_phase = 0.0    # 0.0 → 1.0 breathing animation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_breath)
        self._timer.start(30)
        self.setMinimumSize(280, 260)

    def set_damage(self, value: float):
        self._damage = max(0.0, min(1.0, value))
        self.update()

    def _tick_breath(self):
        speed = 0.015 * (1.0 - self._damage * 0.6)   # damaged = slower breath
        self._breath_phase = (self._breath_phase + speed) % 1.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        p.fillRect(0, 0, w, h, QColor(SURFACE))

        breath = math.sin(self._breath_phase * math.pi * 2) * 0.5 + 0.5
        d = self._damage

        # Colors interpolate healthy→damaged
        def lerp_color(c1, c2, t):
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            return QColor(r, g, b)

        healthy_color = (210, 120, 100)   # pinkish-red
        damaged_color = (60, 35, 25)      # dark brown

        lung_color = lerp_color(healthy_color, damaged_color, d)
        highlight_color = lerp_color((240, 160, 140), (90, 50, 35), d)

        cx = w // 2

        # Draw trachea
        trachea_pen = QPen(QColor(180, 180, 180), 4)
        p.setPen(trachea_pen)
        p.drawLine(cx, 20, cx, 70)
        # bronchi
        p.drawLine(cx, 65, cx - 55, 100)
        p.drawLine(cx, 65, cx + 55, 100)

        # Helper: draw one lung lobe
        def draw_lung(x_center, side):
            scale = 1.0 - d * 0.35 + breath * (1.0 - d) * 0.08
            lw = int(90 * scale)
            lh = int(130 * scale)
            lx = x_center - lw // 2
            ly = 90

            path = QPainterPath()
            if side == "left":
                path.moveTo(x_center, ly)
                path.cubicTo(x_center + lw, ly, x_center + lw, ly + lh,
                             x_center, ly + lh)
                path.cubicTo(x_center - lw * 0.3, ly + lh,
                             x_center - lw * 0.6, ly + lh * 0.5,
                             x_center, ly)
            else:
                path.moveTo(x_center, ly)
                path.cubicTo(x_center - lw, ly, x_center - lw, ly + lh,
                             x_center, ly + lh)
                path.cubicTo(x_center + lw * 0.3, ly + lh,
                             x_center + lw * 0.6, ly + lh * 0.5,
                             x_center, ly)

            grad = QLinearGradient(x_center - lw, ly, x_center + lw, ly + lh)
            grad.setColorAt(0, highlight_color)
            grad.setColorAt(1, lung_color)
            p.setPen(QPen(lung_color.darker(150), 2))
            p.setBrush(QBrush(grad))
            p.drawPath(path)

            # Damage spots (tar/lesions)
            if d > 0.2:
                spot_count = int(d * 10)
                import random
                rng = random.Random(42 + (side == "right"))
                p.setPen(Qt.PenStyle.NoPen)
                for i in range(spot_count):
                    sx = x_center + rng.randint(-int(lw * 0.5), int(lw * 0.5))
                    sy = ly + rng.randint(10, lh - 10)
                    sr = rng.randint(3, 8)
                    darkness = int(30 + d * 40)
                    p.setBrush(QColor(darkness, darkness // 2, darkness // 3, 180))
                    p.drawEllipse(int(sx - sr), int(sy - sr), sr * 2, sr * 2)

        draw_lung(cx - 60, "left")
        draw_lung(cx + 60, "right")

        # Capacity label
        capacity = max(30, int(100 - d * 70))
        label_color = QColor(TEXT_DIM)
        p.setPen(label_color)
        p.setFont(font(11))
        p.drawText(0, h - 32, w, 24, Qt.AlignmentFlag.AlignCenter,
                   f"Lung Capacity: {capacity}%")

        # Capacity bar
        bar_w = int(w * 0.7)
        bar_x = (w - bar_w) // 2
        bar_y = h - 14
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(SURFACE).darker(120))
        p.drawRoundedRect(bar_x, bar_y, bar_w, 8, 4, 4)
        filled = int(bar_w * capacity / 100)
        bar_color = QColor(0, 180 - int(d * 150), int(50 + d * 50))
        if d > 0.6:
            bar_color = QColor(ACCENT)
        p.setBrush(bar_color)
        p.drawRoundedRect(bar_x, bar_y, filled, 8, 4, 4)

        p.end()


class BrainWidget(QWidget):
    """Dopamine wave visualization for the brain."""

    def __init__(self):
        super().__init__()
        self._damage = 0.0
        self._wave_offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)
        self.setMinimumSize(280, 260)

    def set_damage(self, value: float):
        self._damage = max(0.0, min(1.0, value))
        self.update()

    def _tick(self):
        speed = 0.03 + self._damage * 0.02
        self._wave_offset = (self._wave_offset + speed) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(SURFACE))
        d = self._damage

        # Brain outline (simplified)
        brain_cx, brain_cy = w // 2, h // 2 - 20
        brain_rx, brain_ry = 90, 70

        # Brain fill gradient
        healthy_c = QColor(180, 120, 200)
        damaged_c = QColor(80, 50, 60)
        brain_color = QColor(
            int(healthy_c.red() + (damaged_c.red() - healthy_c.red()) * d),
            int(healthy_c.green() + (damaged_c.green() - healthy_c.green()) * d),
            int(healthy_c.blue() + (damaged_c.blue() - healthy_c.blue()) * d),
        )

        grad = QRadialGradient(brain_cx - 20, brain_cy - 20, brain_rx)
        grad.setColorAt(0, brain_color.lighter(130))
        grad.setColorAt(1, brain_color.darker(130))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(brain_color.darker(180), 2))

        # Brain shape using path
        path = QPainterPath()
        path.moveTo(brain_cx, brain_cy - brain_ry)
        path.cubicTo(brain_cx + brain_rx * 1.1, brain_cy - brain_ry,
                     brain_cx + brain_rx, brain_cy + brain_ry * 0.3,
                     brain_cx, brain_cy + brain_ry * 0.5)
        path.cubicTo(brain_cx - brain_rx * 0.5, brain_cy + brain_ry,
                     brain_cx - brain_rx * 1.0, brain_cy + brain_ry * 0.3,
                     brain_cx - brain_rx, brain_cy)
        path.cubicTo(brain_cx - brain_rx * 1.1, brain_cy - brain_ry * 0.5,
                     brain_cx - brain_rx * 0.5, brain_cy - brain_ry,
                     brain_cx, brain_cy - brain_ry)
        p.drawPath(path)

        # Brain folds
        fold_pen = QPen(brain_color.darker(160), 2)
        fold_pen.setStyle(Qt.PenStyle.SolidLine)
        p.setPen(fold_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(4):
            fold_x = brain_cx - 60 + i * 30
            p.drawArc(int(fold_x), int(brain_cy - 30), 30, 60, 0, 180 * 16)

        # Dopamine wave at bottom
        wave_y_base = h - 65
        wave_h = 35 * (1.0 - d * 0.7)   # wave amplitude shrinks with damage
        wave_color = QColor(
            int(50 + d * 200),
            int(200 - d * 180),
            int(50),
        )
        p.setPen(QPen(wave_color, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)

        wave_path = QPainterPath()
        step = 4
        wave_path.moveTo(0, wave_y_base)
        for x in range(0, w + step, step):
            y = wave_y_base - wave_h * math.sin(
                x / w * 4 * math.pi + self._wave_offset
            ) * (1 - d * 0.5)
            if x == 0:
                wave_path.moveTo(x, y)
            else:
                wave_path.lineTo(x, y)
        p.drawPath(wave_path)

        # Label
        receptor_pct = max(25, int(100 - d * 75))
        p.setPen(QColor(TEXT_DIM))
        p.setFont(font(10))
        p.drawText(0, h - 32, w, 16, Qt.AlignmentFlag.AlignCenter,
                   f"Dopamine Receptors: {receptor_pct}%   |   Wave = dopamine activity")
        if d > 0.4:
            p.setPen(QColor(ACCENT))
            p.setFont(font(9, bold=True))
            p.drawText(0, h - 16, w, 14, Qt.AlignmentFlag.AlignCenter,
                       "Craving state — baseline feels like withdrawal")

        p.end()


class HeartWidget(QWidget):
    """Beating heart with artery cross-section showing plaque buildup."""

    def __init__(self):
        super().__init__()
        self._damage = 0.0
        self._beat_phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)
        self.setMinimumSize(280, 260)

    def set_damage(self, value: float):
        self._damage = max(0.0, min(1.0, value))
        self.update()

    def _tick(self):
        bpm = 70 + self._damage * 35   # increases with damage
        increment = (bpm / 60.0) / (1000.0 / 16.0)
        self._beat_phase = (self._beat_phase + increment) % 1.0
        self.update()

    def _heart_scale(self) -> float:
        # systole spike at 0.15, then relax
        t = self._beat_phase
        if t < 0.15:
            return 1.0 + math.sin(t / 0.15 * math.pi) * 0.12
        elif t < 0.35:
            return 1.0 + math.sin((t - 0.15) / 0.2 * math.pi) * 0.06
        return 1.0

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(SURFACE))
        d = self._damage
        scale = self._heart_scale()

        hx, hy = w // 2, h // 2 - 30
        hs = int(55 * scale)

        # Heart color: healthy red → dark purple
        heart_color = QColor(
            int(220 - d * 80),
            int(30 + d * 10),
            int(50 + d * 30),
        )

        # Draw heart using two circles + triangle
        p.setPen(Qt.PenStyle.NoPen)
        grad = QRadialGradient(hx - hs // 4, hy - hs // 4, hs)
        grad.setColorAt(0, heart_color.lighter(140))
        grad.setColorAt(1, heart_color.darker(120))
        p.setBrush(QBrush(grad))

        heart_path = QPainterPath()
        heart_path.moveTo(hx, hy + hs)
        heart_path.cubicTo(hx + hs * 1.5, hy, hx + hs * 1.5, hy - hs,
                           hx, hy - hs * 0.5)
        heart_path.cubicTo(hx - hs * 1.5, hy - hs, hx - hs * 1.5, hy,
                           hx, hy + hs)
        p.drawPath(heart_path)

        # BPM indicator
        bpm = int(70 + d * 35)
        bpm_color = QColor(TEXT) if d < 0.5 else QColor(WARNING)
        p.setPen(bpm_color)
        p.setFont(font(12, bold=True))
        p.drawText(hx - 40, hy - 10, 80, 24,
                   Qt.AlignmentFlag.AlignCenter, f"{bpm} BPM")

        # Artery cross-section (right side)
        ax, ay = w - 75, h // 2 - 10
        ar = 28
        plaque = d * 0.70   # max 70% blockage

        # Outer artery wall
        p.setPen(QPen(QColor(160, 100, 80), 3))
        p.setBrush(QColor(200, 140, 110))
        p.drawEllipse(ax - ar, ay - ar, ar * 2, ar * 2)

        # Plaque ring
        plaque_r = int(ar * (1.0 - plaque))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(180, 150, 60, 200))   # yellowish plaque
        p.drawEllipse(ax - plaque_r, ay - plaque_r, plaque_r * 2, plaque_r * 2)

        # Blood channel (open lumen)
        lumen_r = max(4, int(ar * (1.0 - plaque * 1.1)))
        p.setBrush(QColor(180, 20, 20))
        p.drawEllipse(ax - lumen_r, ay - lumen_r, lumen_r * 2, lumen_r * 2)

        # Artery label
        p.setPen(QColor(TEXT_DIM))
        p.setFont(font(9))
        p.drawText(ax - 35, ay + ar + 6, 70, 14,
                   Qt.AlignmentFlag.AlignCenter, "Artery x-section")
        blockage_pct = int(plaque * 100)
        color = QColor(ACCENT) if blockage_pct > 40 else QColor(TEXT_DIM)
        p.setPen(color)
        p.drawText(ax - 35, ay + ar + 20, 70, 14,
                   Qt.AlignmentFlag.AlignCenter, f"{blockage_pct}% blocked")

        # Legend
        p.setPen(QColor(TEXT_DIM))
        p.setFont(font(9))
        p.drawText(10, h - 18, w // 2, 14, Qt.AlignmentFlag.AlignLeft,
                   "Left: heart  |  Right: artery cross-section")

        p.end()


# ── Clickable body silhouette ──────────────────────────────────────────────────

class BodySilhouette(QWidget):
    """Simple human outline with clickable organ zones."""

    organ_clicked = None   # set by parent

    REGIONS = {
        "brain":  (0.38, 0.04, 0.24, 0.14),   # x, y, w, h as fractions
        "heart":  (0.36, 0.30, 0.28, 0.18),
        "lungs":  (0.25, 0.25, 0.50, 0.25),
    }

    def __init__(self):
        super().__init__()
        self._hovered = None
        self._selected = "lungs"
        self.setMouseTracking(True)
        self.setMinimumSize(160, 360)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _region_rect(self, key):
        fx, fy, fw, fh = self.REGIONS[key]
        w, h = self.width(), self.height()
        return (int(fx * w), int(fy * h), int(fw * w), int(fh * h))

    def _hit_test(self, pos):
        for key in self.REGIONS:
            rx, ry, rw, rh = self._region_rect(key)
            if rx <= pos.x() <= rx + rw and ry <= pos.y() <= ry + rh:
                return key
        return None

    def mouseMoveEvent(self, event):
        hit = self._hit_test(event.pos())
        if hit != self._hovered:
            self._hovered = hit
            self.update()

    def mousePressEvent(self, event):
        hit = self._hit_test(event.pos())
        if hit:
            self._selected = hit
            self.update()
            if self.organ_clicked:
                self.organ_clicked(hit)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(SURFACE))

        body_color = QColor(55, 55, 60)
        outline_pen = QPen(QColor(90, 90, 95), 2)

        cx = w // 2

        def draw_ellipse(fy, fh, fw_frac=0.28):
            bw = int(w * fw_frac)
            bh = int(h * fh)
            bx = cx - bw // 2
            by = int(h * fy)
            p.setPen(outline_pen)
            p.setBrush(body_color)
            p.drawEllipse(bx, by, bw, bh)

        # Head
        draw_ellipse(0.03, 0.12, 0.22)
        # Neck
        nw = int(w * 0.09)
        p.setBrush(body_color)
        p.setPen(outline_pen)
        p.drawRect(cx - nw // 2, int(h * 0.14), nw, int(h * 0.05))
        # Torso
        draw_ellipse(0.18, 0.38, 0.42)
        # Left arm
        aw, ah = int(w * 0.09), int(h * 0.32)
        p.drawRect(cx - int(w * 0.24), int(h * 0.20), aw, ah)
        # Right arm
        p.drawRect(cx + int(w * 0.15), int(h * 0.20), aw, ah)
        # Left leg
        lw, lh = int(w * 0.14), int(h * 0.32)
        p.drawRect(cx - int(w * 0.17), int(h * 0.55), lw, lh)
        # Right leg
        p.drawRect(cx + int(w * 0.04), int(h * 0.55), lw, lh)

        # Organ highlight overlays
        for key, (fx, fy, fw, fh) in self.REGIONS.items():
            rx, ry, rw, rh = int(fx * w), int(fy * h), int(fw * w), int(fh * h)
            if key == self._selected:
                p.setPen(QPen(QColor(ACCENT), 2))
                p.setBrush(QColor(200, 0, 0, 70))
            elif key == self._hovered:
                p.setPen(QPen(QColor(ACCENT2), 1))
                p.setBrush(QColor(200, 0, 0, 35))
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                continue
            p.drawRoundedRect(rx, ry, rw, rh, 6, 6)

            # Label
            p.setPen(QColor(TEXT))
            p.setFont(font(9, bold=True))
            p.drawText(rx, ry, rw, rh, Qt.AlignmentFlag.AlignCenter, key.upper())

        # Static organ labels for non-selected
        for key, (fx, fy, fw, fh) in self.REGIONS.items():
            if key == self._selected:
                continue
            rx, ry, rw, rh = int(fx * w), int(fy * h), int(fw * w), int(fh * h)
            p.setPen(QColor(TEXT_DIM))
            p.setFont(font(8))
            p.drawText(rx, ry, rw, rh, Qt.AlignmentFlag.AlignCenter, key.upper())

        p.end()


# ── Main BodySimulator screen ──────────────────────────────────────────────────

class BodySimulator(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._organ_widgets = {
            "lungs": LungsWidget(),
            "brain": BrainWidget(),
            "heart": HeartWidget(),
        }
        self._current_organ = "lungs"
        self._build_ui()
        fade_in(self)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(12)

        # Back button + title
        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("back_btn")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(lambda: self.main_window.go_to_screen("nav"))
        top.addWidget(back_btn)
        top.addStretch()
        title = QLabel("Your Body on Nicotine")
        title.setFont(font(18, bold=True))
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)

        subtitle = QLabel("Select an organ to see how nicotine damages it over time.")
        subtitle.setFont(font(11))
        subtitle.setStyleSheet(f"color: {TEXT_DIM};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(subtitle)

        # Main body
        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)

        # Left: silhouette
        self.silhouette = BodySilhouette()
        self.silhouette.organ_clicked = self._on_organ_click
        self.silhouette.setFixedWidth(160)
        body_layout.addWidget(self.silhouette)

        # Center: organ visualization
        center = QVBoxLayout()
        self.organ_label = QLabel("LUNGS")
        self.organ_label.setFont(font(16, bold=True))
        self.organ_label.setStyleSheet(f"color: {ACCENT};")
        self.organ_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(self.organ_label)

        # Stack organ widgets
        self.organ_stack = QVBoxLayout()
        for key, widget in self._organ_widgets.items():
            widget.setVisible(key == self._current_organ)
            self.organ_stack.addWidget(widget)
        center.addLayout(self.organ_stack)
        body_layout.addLayout(center, 1)

        # Right: facts panel
        self.facts_frame = QFrame()
        self.facts_frame.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:8px;"
        )
        self.facts_frame.setFixedWidth(220)
        facts_layout = QVBoxLayout(self.facts_frame)
        facts_layout.setContentsMargins(14, 14, 14, 14)
        facts_layout.setSpacing(10)

        self.facts_title = QLabel("Key Facts")
        self.facts_title.setFont(font(12, bold=True))
        facts_layout.addWidget(self.facts_title)

        self.fact_labels = []
        for _ in range(4):
            lbl = QLabel()
            lbl.setWordWrap(True)
            lbl.setFont(font(10))
            lbl.setStyleSheet(f"color: {TEXT_DIM};")
            facts_layout.addWidget(lbl)
            self.fact_labels.append(lbl)
        facts_layout.addStretch()
        body_layout.addWidget(self.facts_frame)

        root.addLayout(body_layout, 1)

        # Sliders
        slider_frame = QFrame()
        slider_frame.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:8px;"
        )
        sl = QVBoxLayout(slider_frame)
        sl.setContentsMargins(20, 12, 20, 12)
        sl.setSpacing(8)

        sl_label = QLabel("Adjust exposure level:")
        sl_label.setFont(font(11, bold=True))
        sl.addWidget(sl_label)

        cig_row = QHBoxLayout()
        cig_lbl = QLabel("Cigarettes/day: ")
        cig_lbl.setFont(font(10))
        cig_row.addWidget(cig_lbl)
        self.cig_slider = QSlider(Qt.Orientation.Horizontal)
        self.cig_slider.setRange(0, 40)
        self.cig_slider.setValue(0)
        self.cig_val = QLabel("0")
        self.cig_val.setFont(font(10, bold=True))
        self.cig_val.setStyleSheet(f"color:{ACCENT};")
        self.cig_val.setFixedWidth(28)
        cig_row.addWidget(self.cig_slider, 1)
        cig_row.addWidget(self.cig_val)
        sl.addLayout(cig_row)

        yr_row = QHBoxLayout()
        yr_lbl = QLabel("Years of use:      ")
        yr_lbl.setFont(font(10))
        yr_row.addWidget(yr_lbl)
        self.yr_slider = QSlider(Qt.Orientation.Horizontal)
        self.yr_slider.setRange(0, 20)
        self.yr_slider.setValue(0)
        self.yr_val = QLabel("0")
        self.yr_val.setFont(font(10, bold=True))
        self.yr_val.setStyleSheet(f"color:{ACCENT};")
        self.yr_val.setFixedWidth(28)
        yr_row.addWidget(self.yr_slider, 1)
        yr_row.addWidget(self.yr_val)
        sl.addLayout(yr_row)

        root.addWidget(slider_frame)

        self.cig_slider.valueChanged.connect(self._update_damage)
        self.yr_slider.valueChanged.connect(self._update_damage)
        self._on_organ_click("lungs")

    def _on_organ_click(self, organ: str):
        self._current_organ = organ
        self.organ_label.setText(organ.upper())
        for key, widget in self._organ_widgets.items():
            widget.setVisible(key == organ)
        facts = ORGAN_FACTS[organ]
        for i, lbl in enumerate(self.fact_labels):
            if i < len(facts):
                lbl.setText(f"• {facts[i]}")
            else:
                lbl.setText("")
        self._update_damage()

    def _update_damage(self):
        cigs = self.cig_slider.value()
        years = self.yr_slider.value()
        self.cig_val.setText(str(cigs))
        self.yr_val.setText(str(years))
        # Damage formula: cigs and years combine non-linearly
        raw = (cigs / 40.0) * 0.6 + (years / 20.0) * 0.4
        damage = min(1.0, raw * (1 + (cigs / 40.0) * (years / 20.0)))
        for widget in self._organ_widgets.values():
            widget.set_damage(damage)
