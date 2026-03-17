"""
graphic_reality.py — Graphic medical visualizations of nicotine damage.
All images are drawn programmatically with QPainter.
Opens with a confirmation warning before showing content.
"""

import math
import random
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (QPainter, QColor, QPen, QBrush, QLinearGradient,
                         QRadialGradient, QPainterPath, QFont)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QScrollArea, QGridLayout,
                              QSizePolicy, QStackedWidget)
from modules.theme import (BG, SURFACE, CARD, ACCENT, ACCENT2, TEXT, TEXT_DIM,
                            WARNING, BORDER, font, fade_in)


# ── Individual medical visualization painters ──────────────────────────────────

class HealthyLungPainter(QWidget):
    """Pink, full, healthy lung cross-section."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(15, 10, 10))

        cx, cy = w // 2, h // 2 + 10

        # Two healthy lobes
        for side in (-1, 1):
            lx = cx + side * 40
            path = QPainterPath()
            path.moveTo(cx, cy - 50)
            if side == 1:
                path.cubicTo(cx + 90, cy - 50, cx + 90, cy + 40, cx, cy + 50)
                path.cubicTo(cx + 20, cy + 50, cx + 20, cy - 50, cx, cy - 50)
            else:
                path.cubicTo(cx - 90, cy - 50, cx - 90, cy + 40, cx, cy + 50)
                path.cubicTo(cx - 20, cy + 50, cx - 20, cy - 50, cx, cy - 50)

            grad = QLinearGradient(cx - 90, cy - 50, cx + 90, cy + 50)
            grad.setColorAt(0, QColor(240, 160, 150))
            grad.setColorAt(0.5, QColor(210, 110, 100))
            grad.setColorAt(1, QColor(180, 80, 70))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor(150, 60, 50), 2))
            p.drawPath(path)

            # Bronchiole texture lines
            p.setPen(QPen(QColor(240, 180, 170, 100), 1))
            for i in range(5):
                x1 = cx + side * (15 + i * 10)
                p.drawLine(x1, cy - 30 + i * 8, x1 + side * 15, cy + 10 + i * 5)

        # Trachea
        p.setPen(QPen(QColor(200, 180, 160), 3))
        p.drawLine(cx, 5, cx, cy - 48)

        # Label
        p.setPen(QColor(100, 220, 100))
        p.setFont(font(9, bold=True))
        p.drawText(0, h - 18, w, 16, Qt.AlignmentFlag.AlignCenter, "HEALTHY — Full capacity")
        p.end()


class DamagedLungPainter(QWidget):
    """Shrunken, dark, spotted emphysemic lung cross-section."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 160)
        self._rng = random.Random(77)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(10, 5, 5))

        cx, cy = w // 2, h // 2 + 10

        for side in (-1, 1):
            # Shrunken (0.65 scale vs healthy)
            path = QPainterPath()
            path.moveTo(cx, cy - 32)
            if side == 1:
                path.cubicTo(cx + 58, cy - 32, cx + 58, cy + 26, cx, cy + 32)
                path.cubicTo(cx + 13, cy + 32, cx + 13, cy - 32, cx, cy - 32)
            else:
                path.cubicTo(cx - 58, cy - 32, cx - 58, cy + 26, cx, cy + 32)
                path.cubicTo(cx - 13, cy + 32, cx - 13, cy - 32, cx, cy - 32)

            grad = QLinearGradient(cx - 60, cy - 35, cx + 60, cy + 35)
            grad.setColorAt(0, QColor(65, 35, 25))
            grad.setColorAt(0.5, QColor(45, 22, 15))
            grad.setColorAt(1, QColor(30, 12, 8))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor(80, 40, 30), 2))
            p.drawPath(path)

            # Tar/lesion spots
            rng = self._rng
            rng.seed(42 + (side == 1))
            p.setPen(Qt.PenStyle.NoPen)
            for _ in range(14):
                sx = cx + side * rng.randint(8, 50)
                sy = cy + rng.randint(-25, 25)
                sr = rng.randint(3, 9)
                darkness = rng.randint(10, 30)
                p.setBrush(QColor(darkness, darkness // 3, darkness // 4, 220))
                p.drawEllipse(sx - sr, sy - sr, sr * 2, sr * 2)

            # Emphysema holes (enlarged air spaces)
            p.setPen(QPen(QColor(20, 10, 8), 1))
            p.setBrush(QColor(15, 8, 5))
            rng.seed(99 + (side == 1))
            for _ in range(6):
                hx = cx + side * rng.randint(10, 45)
                hy = cy + rng.randint(-20, 20)
                hr = rng.randint(4, 10)
                p.drawEllipse(hx - hr, hy - hr, hr * 2, hr * 2)

        # Trachea (thickened, inflamed wall)
        p.setPen(QPen(QColor(120, 80, 60), 4))
        p.drawLine(cx, 5, cx, cy - 30)

        p.setPen(QColor(220, 60, 60))
        p.setFont(font(9, bold=True))
        p.drawText(0, h - 18, w, 16, Qt.AlignmentFlag.AlignCenter,
                   "EMPHYSEMA — 40% capacity lost")
        p.end()


class HealthyArteryPainter(QWidget):
    """Clean artery cross-section with open lumen."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(10, 8, 8))

        cx, cy = w // 2, h // 2

        # Outer wall
        p.setPen(QPen(QColor(180, 120, 90), 3))
        p.setBrush(QColor(200, 145, 110))
        p.drawEllipse(cx - 55, cy - 55, 110, 110)

        # Muscle layer
        p.setPen(QPen(QColor(160, 90, 70), 2))
        p.setBrush(QColor(180, 110, 85))
        p.drawEllipse(cx - 45, cy - 45, 90, 90)

        # Clean lumen (blood)
        grad = QRadialGradient(cx, cy, 38)
        grad.setColorAt(0, QColor(220, 30, 30))
        grad.setColorAt(1, QColor(160, 10, 10))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(cx - 38, cy - 38, 76, 76)

        # Labels
        p.setPen(QColor(100, 220, 100))
        p.setFont(font(9, bold=True))
        p.drawText(0, h - 18, w, 16, Qt.AlignmentFlag.AlignCenter,
                   "HEALTHY — Lumen fully open")

        # Annotation lines
        p.setPen(QPen(QColor(TEXT_DIM), 1, Qt.PenStyle.DotLine))
        p.setFont(font(8))
        p.setPen(QColor(TEXT_DIM))
        p.drawText(cx + 58, cy - 10, 60, 20, Qt.AlignmentFlag.AlignLeft, "Wall")
        p.drawText(cx + 40, cy + 20, 60, 20, Qt.AlignmentFlag.AlignLeft, "Lumen")
        p.end()


class BlockedArteryPainter(QWidget):
    """Artery with 75% plaque blockage — atherosclerosis."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(10, 8, 8))

        cx, cy = w // 2, h // 2

        # Outer wall (thickened)
        p.setPen(QPen(QColor(140, 80, 60), 3))
        p.setBrush(QColor(165, 105, 80))
        p.drawEllipse(cx - 55, cy - 55, 110, 110)

        # Plaque layer (thick, uneven)
        plaque_path = QPainterPath()
        plaque_path.addEllipse(QRectF(cx - 44, cy - 44, 88, 88))
        plaque_grad = QRadialGradient(cx, cy, 44)
        plaque_grad.setColorAt(0, QColor(200, 170, 70))
        plaque_grad.setColorAt(0.7, QColor(180, 140, 50))
        plaque_grad.setColorAt(1, QColor(150, 110, 30))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(plaque_grad))
        p.drawPath(plaque_path)

        # Calcification specks
        rng = random.Random(55)
        for _ in range(8):
            sx = cx + rng.randint(-35, 35)
            sy = cy + rng.randint(-35, 35)
            sr = rng.randint(3, 7)
            p.setBrush(QColor(230, 230, 210, 200))
            p.drawEllipse(sx - sr, sy - sr, sr * 2, sr * 2)

        # Tiny remaining lumen
        lumen_r = 12
        p.setBrush(QColor(160, 10, 10))
        p.drawEllipse(cx - lumen_r, cy - lumen_r, lumen_r * 2, lumen_r * 2)

        p.setPen(QColor(220, 60, 60))
        p.setFont(font(9, bold=True))
        p.drawText(0, h - 18, w, 16, Qt.AlignmentFlag.AlignCenter,
                   "ATHEROSCLEROSIS — 75% blocked")
        p.end()


class BrainScanHealthy(QWidget):
    """Simulated fMRI-style brain activity scan — healthy."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(5, 5, 15))

        cx, cy = w // 2, h // 2 - 5
        # Brain outline
        brain_path = QPainterPath()
        brain_path.moveTo(cx, cy - 50)
        brain_path.cubicTo(cx + 65, cy - 50, cx + 65, cy + 30, cx, cy + 40)
        brain_path.cubicTo(cx - 65, cy + 30, cx - 65, cy - 50, cx, cy - 50)

        # Dark base
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 15, 30))
        p.drawPath(brain_path)

        # Activity hotspots — bright colors like real fMRI
        hotspots = [
            (cx - 20, cy - 20, 22, QColor(255, 50, 50, 200)),    # frontal
            (cx + 25, cy - 15, 18, QColor(255, 120, 0, 180)),    # parietal
            (cx, cy + 15, 20, QColor(255, 200, 0, 190)),          # temporal
            (cx - 30, cy + 10, 15, QColor(200, 255, 50, 160)),   # occipital
            (cx + 15, cy, 14, QColor(100, 200, 255, 150)),        # association
        ]
        for hx, hy, hr, color in hotspots:
            grad = QRadialGradient(hx, hy, hr)
            grad.setColorAt(0, color)
            grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            p.setBrush(QBrush(grad))
            p.drawEllipse(hx - hr, hy - hr, hr * 2, hr * 2)

        p.setPen(QPen(QColor(80, 80, 120), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(brain_path)

        p.setPen(QColor(100, 220, 100))
        p.setFont(font(9, bold=True))
        p.drawText(0, h - 18, w, 16, Qt.AlignmentFlag.AlignCenter,
                   "HEALTHY — Normal activity")
        p.end()


class BrainScanDamaged(QWidget):
    """fMRI-style brain scan — nicotine-dependent, reduced prefrontal activity."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(5, 5, 15))

        cx, cy = w // 2, h // 2 - 5
        brain_path = QPainterPath()
        brain_path.moveTo(cx, cy - 50)
        brain_path.cubicTo(cx + 65, cy - 50, cx + 65, cy + 30, cx, cy + 40)
        brain_path.cubicTo(cx - 65, cy + 30, cx - 65, cy - 50, cx, cy - 50)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 15, 30))
        p.drawPath(brain_path)

        # Reduced activity — fewer, dimmer hotspots; cravings area bright
        hotspots = [
            (cx - 20, cy - 20, 10, QColor(80, 20, 20, 120)),    # frontal REDUCED
            (cx + 25, cy - 15, 8, QColor(60, 40, 0, 100)),      # parietal REDUCED
            (cx, cy + 15, 8, QColor(80, 60, 0, 110)),            # temporal REDUCED
            # Craving center — hyperactive
            (cx + 5, cy + 5, 25, QColor(255, 0, 0, 230)),        # nucleus accumbens
        ]
        for hx, hy, hr, color in hotspots:
            grad = QRadialGradient(hx, hy, hr)
            grad.setColorAt(0, color)
            grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            p.setBrush(QBrush(grad))
            p.drawEllipse(hx - hr, hy - hr, hr * 2, hr * 2)

        p.setPen(QPen(QColor(80, 30, 30), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(brain_path)

        # Craving label
        p.setPen(QColor(255, 80, 80))
        p.setFont(font(8))
        p.drawText(cx - 10, cy + 30, 80, 14,
                   Qt.AlignmentFlag.AlignLeft, "← craving center")

        p.setPen(QColor(220, 60, 60))
        p.setFont(font(9, bold=True))
        p.drawText(0, h - 18, w, 16, Qt.AlignmentFlag.AlignCenter,
                   "DEPENDENT — Prefrontal cortex suppressed")
        p.end()


class OralLesionPainter(QWidget):
    """Simplified oral tissue cross-section showing lesion/leukoplakia."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(10, 5, 5))

        # Gum tissue base (unhealthy)
        tissue_grad = QLinearGradient(0, 20, 0, h - 20)
        tissue_grad.setColorAt(0, QColor(160, 60, 60))
        tissue_grad.setColorAt(0.5, QColor(130, 50, 45))
        tissue_grad.setColorAt(1, QColor(100, 35, 30))
        p.setBrush(QBrush(tissue_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(10, 20, w - 20, h - 40)

        # Tooth remnants
        for i, tx in enumerate([w // 2 - 35, w // 2, w // 2 + 35]):
            tooth_color = QColor(200, 180, 130) if i != 1 else QColor(120, 90, 50)
            p.setBrush(tooth_color)
            p.setPen(QPen(QColor(80, 60, 40), 1))
            p.drawRoundedRect(tx - 12, 20, 22, 35, 4, 4)

        # Leukoplakia patches (white pre-cancerous)
        rng = random.Random(31)
        for _ in range(4):
            lx = rng.randint(15, w - 50)
            ly = rng.randint(55, h - 45)
            lw = rng.randint(18, 40)
            lh = rng.randint(10, 20)
            p.setBrush(QColor(230, 225, 200, 200))
            p.setPen(QPen(QColor(200, 190, 160), 1))
            p.drawRoundedRect(lx, ly, lw, lh, 5, 5)

        # Main lesion (reddish ulceration)
        lesion_cx = w // 2 + 20
        lesion_cy = h // 2 + 15
        for radius, alpha in [(20, 180), (14, 220), (8, 255)]:
            color = QColor(200 - radius * 2, 20, 20, alpha)
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(lesion_cx - radius, lesion_cy - radius, radius * 2, radius * 2)

        # Recession indicator
        p.setPen(QColor(220, 60, 60))
        p.setFont(font(9, bold=True))
        p.drawText(0, h - 18, w, 16, Qt.AlignmentFlag.AlignCenter,
                   "ORAL LESION — Leukoplakia / Pre-cancerous")
        p.end()


# ── Medical condition card ─────────────────────────────────────────────────────

CONDITION_DATA = [
    {
        "title":    "Healthy Lung",
        "severity": "BASELINE",
        "sev_color":"#00aa44",
        "desc":     "Full capacity. Cilia working. Alveoli intact. CO₂ exchange normal.",
        "painter":  HealthyLungPainter,
    },
    {
        "title":    "Emphysema",
        "severity": "SEVERE",
        "sev_color":"#cc0000",
        "desc":     "Alveolar walls destroyed. Permanent air trapping. Breathing requires constant effort. "
                    "Develops after 10-20 years of heavy smoking. Not reversible.",
        "painter":  DamagedLungPainter,
    },
    {
        "title":    "Healthy Artery",
        "severity": "BASELINE",
        "sev_color":"#00aa44",
        "desc":     "Smooth endothelium. Full lumen. Blood flows without resistance.",
        "painter":  HealthyArteryPainter,
    },
    {
        "title":    "Atherosclerosis",
        "severity": "CRITICAL",
        "sev_color":"#cc0000",
        "desc":     "75% blockage from plaque and calcified deposits. Risk of clot, heart attack, or stroke. "
                    "Smokers develop this condition 10 years earlier on average.",
        "painter":  BlockedArteryPainter,
    },
    {
        "title":    "Healthy Brain (fMRI)",
        "severity": "BASELINE",
        "sev_color":"#00aa44",
        "desc":     "Normal prefrontal activity. Balanced dopamine. Reward system functioning without external triggers.",
        "painter":  BrainScanHealthy,
    },
    {
        "title":    "Nicotine-Dependent Brain",
        "severity": "ALTERED",
        "sev_color":"#ff6600",
        "desc":     "Prefrontal cortex suppressed. Reward system hijacked. Craving center (nucleus accumbens) "
                    "hyperactive. Emotional regulation impaired.",
        "painter":  BrainScanDamaged,
    },
    {
        "title":    "Oral Tissue Damage",
        "severity": "SEVERE",
        "sev_color":"#cc0000",
        "desc":     "Leukoplakia (white patches) and ulcerative lesions. Gum recession. Precancerous changes. "
                    "Oral cancer risk is 6× higher in smokers.",
        "painter":  OralLesionPainter,
    },
]


class ConditionCard(QFrame):
    def __init__(self, data: dict):
        super().__init__()
        self.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:8px;"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Title row
        title_row = QHBoxLayout()
        title_lbl = QLabel(data["title"])
        title_lbl.setFont(font(11, bold=True))
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        sev_badge = QLabel(f"  {data['severity']}  ")
        sev_badge.setFont(font(9, bold=True))
        sev_badge.setStyleSheet(
            f"background:{data['sev_color']}; color:#ffffff; border-radius:4px;"
        )
        title_row.addWidget(sev_badge)
        layout.addLayout(title_row)

        # Visualization
        painter_widget = data["painter"]()
        painter_widget.setFixedHeight(160)
        layout.addWidget(painter_widget)

        # Description
        desc_lbl = QLabel(data["desc"])
        desc_lbl.setWordWrap(True)
        desc_lbl.setFont(font(9))
        desc_lbl.setStyleSheet(f"color:{TEXT_DIM};")
        layout.addWidget(desc_lbl)


# ── Warning gate ──────────────────────────────────────────────────────────────

class WarningGate(QWidget):
    def __init__(self, on_continue, on_back):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)

        icon = QLabel("⚠")
        icon.setFont(font(52))
        icon.setStyleSheet(f"color:{WARNING};")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        heading = QLabel("Content Warning")
        heading.setFont(font(22, bold=True))
        heading.setStyleSheet(f"color:{ACCENT};")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)

        msg = QLabel(
            "This section contains disturbing medical imagery showing the\n"
            "real effects of long-term nicotine use.\n\n"
            "Visualizations include: emphysemic lung tissue, arterial blockage,\n"
            "altered brain scans, and oral lesions.\n\n"
            "This content is for educational purposes only."
        )
        msg.setFont(font(12))
        msg.setStyleSheet(f"color:{TEXT_DIM};")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        back_btn = QPushButton("← Go Back")
        back_btn.setObjectName("secondary")
        back_btn.setFixedWidth(160)
        back_btn.clicked.connect(on_back)
        btn_row.addWidget(back_btn)

        cont_btn = QPushButton("I Understand — Continue")
        cont_btn.setFixedWidth(240)
        cont_btn.clicked.connect(on_continue)
        btn_row.addWidget(cont_btn)

        layout.addLayout(btn_row)


# ── Main GraphicReality screen ────────────────────────────────────────────────

class GraphicReality(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._stack = QStackedWidget(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._stack)

        # Page 0: warning gate
        gate = WarningGate(
            on_continue=self._show_content,
            on_back=lambda: self.main_window.go_to_screen("nav"),
        )
        self._stack.addWidget(gate)

        # Page 1: content
        self._content_widget = self._build_content()
        self._stack.addWidget(self._content_widget)

        self._stack.setCurrentIndex(0)
        fade_in(self)

    def _build_content(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # Back + title
        top = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("back_btn")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(lambda: self.main_window.go_to_screen("nav"))
        top.addWidget(back_btn)
        top.addStretch()
        title = QLabel("Graphic Reality: The Medical Truth")
        title.setFont(font(18, bold=True))
        title.setStyleSheet(f"color:{ACCENT};")
        top.addWidget(title)
        top.addStretch()
        layout.addLayout(top)

        subtitle = QLabel(
            "All visualizations are medical-accuracy reconstructions. "
            "These conditions are real and common among long-term nicotine users."
        )
        subtitle.setFont(font(10))
        subtitle.setStyleSheet(f"color:{TEXT_DIM};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Scrollable grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setSpacing(14)

        for i, cdata in enumerate(CONDITION_DATA):
            card = ConditionCard(cdata)
            grid.addWidget(card, i // 2, i % 2)

        scroll.setWidget(grid_widget)
        layout.addWidget(scroll, 1)

        return container

    def _show_content(self):
        self._stack.setCurrentIndex(1)
        fade_in(self._content_widget)
