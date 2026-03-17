"""
preview_panel.py — Mosko Photo Labs
Center panel: large image preview with navigation, zoom, and info overlay.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread, QSize, QRect, QPoint
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QFont, QKeyEvent, QWheelEvent
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QScrollArea, QSlider
)

from app.constants import COLORS, PREVIEW_MAX
from app.models.image_model import ImageFile


class _ImageLoader(QThread):
    """Load a full-size preview in a background thread."""
    loaded = Signal(QPixmap)

    def __init__(self, image: ImageFile):
        super().__init__()
        self._image = image

    def run(self):
        pix = self._load()
        self.loaded.emit(pix)

    def _load(self) -> QPixmap:
        filepath = self._image.filepath
        ext = filepath.suffix.lower()
        from app.constants import RAW_EXTENSIONS

        if ext in RAW_EXTENSIONS:
            try:
                import rawpy
                import numpy as np
                with rawpy.imread(str(filepath)) as raw:
                    rgb = raw.postprocess(
                        use_camera_wb=True,
                        half_size=True,
                        no_auto_bright=False,
                    )
                h, w, ch = rgb.shape
                img = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
                pix = QPixmap.fromImage(img)
                return pix.scaled(
                    PREVIEW_MAX[0], PREVIEW_MAX[1],
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            except Exception:
                pass

        # Standard formats via Qt
        pix = QPixmap(str(filepath))
        if not pix.isNull():
            return pix.scaled(
                PREVIEW_MAX[0], PREVIEW_MAX[1],
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        # Pillow fallback
        try:
            from PIL import Image as PilImage
            im = PilImage.open(filepath)
            im.thumbnail(PREVIEW_MAX, PilImage.LANCZOS)
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            pix = QPixmap()
            pix.loadFromData(buf.getvalue())
            return pix
        except Exception:
            return QPixmap()


class _ZoomableLabel(QLabel):
    """QLabel that supports scroll-wheel zoom."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_pix: Optional[QPixmap] = None
        self._zoom = 1.0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 200)

    def set_pixmap(self, pix: QPixmap):
        self._base_pix = pix
        self._zoom = 1.0
        self._apply_zoom()

    def fit_to_window(self):
        self._zoom = 1.0
        self._apply_zoom()

    def zoom_in(self):
        self._zoom = min(self._zoom * 1.25, 8.0)
        self._apply_zoom()

    def zoom_out(self):
        self._zoom = max(self._zoom / 1.25, 0.1)
        self._apply_zoom()

    def _apply_zoom(self):
        if self._base_pix is None or self._base_pix.isNull():
            return
        if self._zoom == 1.0:
            target = self._base_pix.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            w = int(self._base_pix.width() * self._zoom)
            h = int(self._base_pix.height() * self._zoom)
            target = self._base_pix.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        super().setPixmap(target)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def resizeEvent(self, event):
        if self._zoom == 1.0:
            self._apply_zoom()
        super().resizeEvent(event)


class PreviewPanel(QFrame):
    """
    Center panel: image preview + navigation controls + metadata overlay.
    """

    prev_requested = Signal()
    next_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewPanel")
        self._current_image: Optional[ImageFile] = None
        self._loader: Optional[_ImageLoader] = None
        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Top bar: filename + zoom controls
        top_bar = QWidget()
        top_bar.setStyleSheet(f"background:{COLORS['bg_toolbar']};"
                               f"border-bottom:1px solid {COLORS['border']};")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 6, 10, 6)
        top_layout.setSpacing(8)

        self._filename_label = QLabel("No image selected")
        self._filename_label.setObjectName("PanelTitle")
        top_layout.addWidget(self._filename_label, 1)

        btn_zoom_out = QPushButton("−")
        btn_zoom_fit = QPushButton("Fit")
        btn_zoom_in  = QPushButton("+")
        for b in (btn_zoom_out, btn_zoom_fit, btn_zoom_in):
            b.setFixedSize(32, 28)
        btn_zoom_out.clicked.connect(lambda: self._img_label.zoom_out())
        btn_zoom_fit.clicked.connect(lambda: self._img_label.fit_to_window())
        btn_zoom_in.clicked.connect(lambda: self._img_label.zoom_in())
        top_layout.addWidget(btn_zoom_out)
        top_layout.addWidget(btn_zoom_fit)
        top_layout.addWidget(btn_zoom_in)

        outer.addWidget(top_bar)

        # Scroll area for the image
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setStyleSheet("background: #0d0d0d; border: none;")

        self._img_label = _ZoomableLabel()
        scroll.setWidget(self._img_label)
        outer.addWidget(scroll, 1)

        # Info overlay bar (bottom)
        info_bar = QWidget()
        info_bar.setStyleSheet(f"background:{COLORS['bg_toolbar']};"
                                f"border-top:1px solid {COLORS['border']};")
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(10, 6, 10, 6)
        info_layout.setSpacing(16)

        btn_prev = QPushButton("◀  Prev")
        btn_next = QPushButton("Next  ▶")
        btn_prev.clicked.connect(self.prev_requested)
        btn_next.clicked.connect(self.next_requested)
        btn_prev.setFixedWidth(90)
        btn_next.setFixedWidth(90)

        self._info_camera  = QLabel("")
        self._info_camera.setObjectName("CameraInfo")
        self._info_settings = QLabel("")
        self._info_settings.setObjectName("CameraInfo")
        self._info_gps = QLabel("")
        self._info_gps.setObjectName("GpsLabel")
        self._info_dims = QLabel("")
        self._info_dims.setObjectName("CameraInfo")
        self._loading_label = QLabel("Loading…")
        self._loading_label.setObjectName("CameraInfo")
        self._loading_label.setVisible(False)

        info_layout.addWidget(btn_prev)
        info_layout.addWidget(self._info_camera, 2)
        info_layout.addWidget(self._info_settings, 2)
        info_layout.addWidget(self._info_gps, 1)
        info_layout.addWidget(self._info_dims, 1)
        info_layout.addWidget(self._loading_label)
        info_layout.addWidget(btn_next)

        outer.addWidget(info_bar)

    # ── Public API ────────────────────────────────────────────────────────

    def show_image(self, image: ImageFile):
        self._current_image = image

        if not image._loaded:
            image.load_exif()

        # Header
        self._filename_label.setText(image.filename)
        self._update_info_bar(image)

        # Show loading spinner while image loads
        self._loading_label.setVisible(True)
        self._img_label.setText("Loading…")

        # Cancel previous loader
        if self._loader and self._loader.isRunning():
            self._loader.quit()

        self._loader = _ImageLoader(image)
        self._loader.loaded.connect(self._on_image_loaded)
        self._loader.start()

    def _on_image_loaded(self, pix: QPixmap):
        self._loading_label.setVisible(False)
        if pix.isNull():
            self._img_label.setText("Cannot preview this file")
            return
        self._img_label.set_pixmap(pix)
        # Update dimensions
        self._info_dims.setText(f"{pix.width()}×{pix.height()}")

    def _update_info_bar(self, image: ImageFile):
        # Camera
        self._info_camera.setText(image.camera_summary)

        # Exposure settings
        exif = image.exif
        parts = []
        if exif.get("FNumber"):
            from app.core.exif_engine import format_aperture
            parts.append(format_aperture(exif["FNumber"]))
        if exif.get("ExposureTime"):
            from app.core.exif_engine import format_exposure
            parts.append(format_exposure(exif["ExposureTime"]))
        if exif.get("ISOSpeedRatings"):
            iso = exif["ISOSpeedRatings"]
            parts.append(f"ISO {iso}")
        if exif.get("FocalLength"):
            fl = exif["FocalLength"]
            if isinstance(fl, float):
                parts.append(f"{fl:.0f}mm")
            elif isinstance(fl, (list, tuple)) and len(fl) == 2:
                parts.append(f"{fl[0]/fl[1]:.0f}mm")
        self._info_settings.setText("  ·  ".join(parts))

        # GPS
        if image.has_gps:
            lat = exif.get("_GPSLatDecimal")
            lon = exif.get("_GPSLonDecimal")
            if lat is not None and lon is not None:
                self._info_gps.setText(f"📍 {lat:.4f}, {lon:.4f}")
            else:
                self._info_gps.setText("📍 GPS")
        else:
            self._info_gps.setText("")

    def clear(self):
        self._current_image = None
        self._img_label.setText("")
        self._filename_label.setText("No image selected")
        self._info_camera.setText("")
        self._info_settings.setText("")
        self._info_gps.setText("")
        self._info_dims.setText("")
