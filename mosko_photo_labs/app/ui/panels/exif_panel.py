"""
exif_panel.py — Mosko Photo Labs
Right panel: tabbed EXIF editor with Camera / Lens / GPS / Copyright / All tabs.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QScrollArea,
    QLabel, QLineEdit, QComboBox, QPushButton, QTabWidget,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy, QGroupBox
)

from app.constants import COLORS, EXIF_SECTIONS, EXIF_CHOICES
from app.core.exif_engine import format_exposure, format_aperture
from app.core.gps_utils import format_dms, google_maps_url
from app.models.image_model import ImageFile


class _FieldRow(QWidget):
    """A single label + input row in the EXIF editor."""

    changed = Signal(str, str)   # field_key, new_value

    def __init__(self, key: str, label: str, value_type: str, editable: bool, parent=None):
        super().__init__(parent)
        self.key = key
        self.value_type = value_type
        self._original_value: Any = None
        self._is_modified = False

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 1, 0, 1)
        row.setSpacing(6)

        # Modified dot
        self._dot = QLabel("●")
        self._dot.setObjectName("Modified")
        self._dot.setFixedWidth(12)
        self._dot.setVisible(False)
        row.addWidget(self._dot)

        # Input widget
        if value_type == "choice" and key in EXIF_CHOICES:
            self._input = QComboBox()
            choices = EXIF_CHOICES[key]
            for k, v in choices.items():
                self._input.addItem(v, k)
            self._input.currentIndexChanged.connect(self._on_combo_changed)
        else:
            self._input = QLineEdit()
            self._input.setReadOnly(not editable)
            if not editable:
                self._input.setToolTip("Read-only field")
                self._input.setStyleSheet(f"color: {COLORS['text_secondary']};")
            self._input.textChanged.connect(self._on_text_changed)

        row.addWidget(self._input, 1)

    def set_value(self, value: Any):
        self._original_value = value
        self._is_modified = False
        self._dot.setVisible(False)

        if isinstance(self._input, QComboBox):
            idx = self._input.findData(value)
            self._input.blockSignals(True)
            self._input.setCurrentIndex(idx if idx >= 0 else 0)
            self._input.blockSignals(False)
        else:
            self._input.blockSignals(True)
            self._input.setText(self._format_display(value))
            self._input.blockSignals(False)
            self._input.setProperty("modified", False)
            self._input.style().unpolish(self._input)
            self._input.style().polish(self._input)

    def clear_value(self):
        self.set_value("")

    def _format_display(self, value: Any) -> str:
        if value is None or value == "":
            return ""
        if self.value_type == "exposure":
            return format_exposure(value)
        if self.value_type == "aperture":
            return format_aperture(value)
        if self.value_type in ("rational",) and isinstance(value, (tuple, list)):
            if len(value) == 2 and value[1] != 0:
                return str(round(value[0] / value[1], 4))
        if self.value_type in ("gps_lat", "gps_lon"):
            return str(value)
        return str(value)

    def _on_text_changed(self, text: str):
        was_modified = self._is_modified
        self._is_modified = text != self._format_display(self._original_value)
        if self._is_modified != was_modified:
            self._dot.setVisible(self._is_modified)
            self._input.setProperty("modified", self._is_modified)
            self._input.style().unpolish(self._input)
            self._input.style().polish(self._input)
        if self._is_modified:
            self.changed.emit(self.key, text)

    def _on_combo_changed(self):
        data = self._input.currentData()
        self.changed.emit(self.key, str(data))

    def current_text(self) -> str:
        if isinstance(self._input, QComboBox):
            return str(self._input.currentData())
        return self._input.text()

    def mark_modified(self):
        self._is_modified = True
        self._dot.setVisible(True)

    @property
    def is_modified(self) -> bool:
        return self._is_modified


class _SectionWidget(QWidget):
    """A labelled group of _FieldRow widgets for one EXIF section."""

    field_changed = Signal(str, str)

    def __init__(self, section_name: str, fields, parent=None):
        super().__init__(parent)
        self._rows: Dict[str, _FieldRow] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        # Section header
        header = QLabel(section_name.upper())
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        # Form rows
        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 8)
        form.setSpacing(4)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        for key, label, _ifd, _tag, vtype, editable in fields:
            lbl = QLabel(label + ":")
            lbl.setObjectName("FieldLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row_widget = _FieldRow(key, label, vtype, editable)
            row_widget.changed.connect(self.field_changed)
            self._rows[key] = row_widget
            form.addRow(lbl, row_widget)

        layout.addLayout(form)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {COLORS['border']};")
        layout.addWidget(line)

    def populate(self, exif: Dict[str, Any]):
        for key, row in self._rows.items():
            row.set_value(exif.get(key, ""))

    def collect(self) -> Dict[str, str]:
        return {k: row.current_text() for k, row in self._rows.items()
                if row.is_modified}

    def clear(self):
        for row in self._rows.values():
            row.clear_value()


class ExifPanel(QFrame):
    """
    Right panel: tabbed EXIF editor.
    Emits exif_changed(dict) when user modifies fields.
    """

    exif_changed = Signal(dict)   # {key: value}
    save_requested  = Signal()
    revert_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ExifPanel")
        self.setMinimumWidth(300)
        self.setMaximumWidth(420)

        self._current_image: Optional[ImageFile] = None
        self._sections: Dict[str, _SectionWidget] = {}
        self._pending_changes: Dict[str, str] = {}

        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Panel title bar
        title_bar = QWidget()
        title_bar.setStyleSheet(
            f"background:{COLORS['bg_toolbar']};"
            f"border-bottom: 1px solid {COLORS['border']};"
        )
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(10, 6, 10, 6)
        title_lbl = QLabel("EXIF EDITOR")
        title_lbl.setObjectName("SectionHeader")
        tb_layout.addWidget(title_lbl, 1)
        outer.addWidget(title_bar)

        # Tabs
        self._tabs = QTabWidget()
        outer.addWidget(self._tabs, 1)

        # Build one scroll tab per section
        for section_name, fields in EXIF_SECTIONS.items():
            sw = _SectionWidget(section_name, fields)
            sw.field_changed.connect(self._on_field_changed)
            self._sections[section_name] = sw

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(sw)
            self._tabs.addTab(scroll, section_name)

        # GPS extras tab
        self._gps_extra_tab = self._build_gps_extra_tab()
        self._tabs.insertTab(3, self._gps_extra_tab, "📍 Map")

        # All fields tab
        self._all_table = QTableWidget()
        self._all_table.setColumnCount(2)
        self._all_table.setHorizontalHeaderLabels(["Field", "Value"])
        self._all_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._all_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabs.addTab(self._all_table, "All")

        # Bottom action bar
        action_bar = QWidget()
        action_bar.setStyleSheet(
            f"background:{COLORS['bg_toolbar']};"
            f"border-top: 1px solid {COLORS['border']};"
        )
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(10, 6, 10, 6)
        ab_layout.setSpacing(8)

        self._dirty_label = QLabel("")
        self._dirty_label.setObjectName("Modified")
        ab_layout.addWidget(self._dirty_label, 1)

        self._btn_revert = QPushButton("Revert")
        self._btn_revert.setEnabled(False)
        self._btn_revert.clicked.connect(self._do_revert)
        ab_layout.addWidget(self._btn_revert)

        self._btn_save = QPushButton("Save")
        self._btn_save.setObjectName("AccentButton")
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._do_save)
        ab_layout.addWidget(self._btn_save)

        outer.addWidget(action_bar)

    def _build_gps_extra_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        hdr = QLabel("GPS LOCATION")
        hdr.setObjectName("SectionHeader")
        layout.addWidget(hdr)

        # Decimal input
        form = QFormLayout()
        form.setSpacing(6)
        self._gps_lat_edit = QLineEdit()
        self._gps_lat_edit.setPlaceholderText("e.g. 40.7580 or 40.7580 N")
        self._gps_lon_edit = QLineEdit()
        self._gps_lon_edit.setPlaceholderText("e.g. -73.9855 or 73.9855 W")
        lbl_lat = QLabel("Latitude:")
        lbl_lat.setObjectName("FieldLabel")
        lbl_lon = QLabel("Longitude:")
        lbl_lon.setObjectName("FieldLabel")
        form.addRow(lbl_lat, self._gps_lat_edit)
        form.addRow(lbl_lon, self._gps_lon_edit)
        layout.addLayout(form)

        # DMS display
        self._gps_dms_label = QLabel("")
        self._gps_dms_label.setObjectName("CameraInfo")
        self._gps_dms_label.setWordWrap(True)
        layout.addWidget(self._gps_dms_label)

        # Apply GPS button
        btn_apply_gps = QPushButton("Apply GPS to Image")
        btn_apply_gps.setObjectName("AccentButton")
        btn_apply_gps.clicked.connect(self._apply_gps)
        layout.addWidget(btn_apply_gps)

        # Open in maps
        maps_row = QHBoxLayout()
        btn_gmaps = QPushButton("🗺  Google Maps")
        btn_amaps = QPushButton("🍎  Apple Maps")
        btn_gmaps.clicked.connect(self._open_google_maps)
        btn_amaps.clicked.connect(self._open_apple_maps)
        maps_row.addWidget(btn_gmaps)
        maps_row.addWidget(btn_amaps)
        layout.addLayout(maps_row)

        # Altitude
        alt_form = QFormLayout()
        self._gps_alt_edit = QLineEdit()
        self._gps_alt_edit.setPlaceholderText("metres above sea level")
        lbl_alt = QLabel("Altitude (m):")
        lbl_alt.setObjectName("FieldLabel")
        alt_form.addRow(lbl_alt, self._gps_alt_edit)
        layout.addLayout(alt_form)

        layout.addStretch()
        return w

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_field_changed(self, key: str, value: str):
        self._pending_changes[key] = value
        self._btn_save.setEnabled(True)
        self._btn_revert.setEnabled(True)
        n = len(self._pending_changes)
        self._dirty_label.setText(f"{n} change{'s' if n != 1 else ''}")
        self.exif_changed.emit({key: value})

    def _do_save(self):
        if self._current_image:
            self._current_image.set_fields(self._pending_changes)
        self._pending_changes.clear()
        self._btn_save.setEnabled(False)
        self._btn_revert.setEnabled(False)
        self._dirty_label.setText("")
        self.save_requested.emit()

    def _do_revert(self):
        self._pending_changes.clear()
        self._btn_save.setEnabled(False)
        self._btn_revert.setEnabled(False)
        self._dirty_label.setText("")
        if self._current_image:
            self.populate(self._current_image)
        self.revert_requested.emit()

    def _apply_gps(self):
        from app.core.gps_utils import parse_decimal_input, format_dms
        lat_text = self._gps_lat_edit.text().strip()
        lon_text = self._gps_lon_edit.text().strip()
        if not lat_text or not lon_text:
            return
        lat = parse_decimal_input(lat_text)
        lon = parse_decimal_input(lon_text)
        if lat is None or lon is None:
            return
        # Update DMS display
        self._gps_dms_label.setText(
            f"{format_dms(lat, True)}\n{format_dms(lon, False)}"
        )
        changes = {
            "GPSLatitude": lat,
            "GPSLongitude": lon,
            "_GPSLatDecimal": lat,
            "_GPSLonDecimal": lon,
        }
        # Alt
        alt_text = self._gps_alt_edit.text().strip()
        if alt_text:
            try:
                changes["GPSAltitude"] = float(alt_text)
            except ValueError:
                pass
        if self._current_image:
            self._current_image.set_fields(changes)
        self._pending_changes.update(changes)
        self._btn_save.setEnabled(True)
        self._btn_revert.setEnabled(True)
        self.exif_changed.emit(changes)

    def _open_google_maps(self):
        from app.core.gps_utils import parse_decimal_input, google_maps_url
        import webbrowser
        lat = parse_decimal_input(self._gps_lat_edit.text())
        lon = parse_decimal_input(self._gps_lon_edit.text())
        if lat is not None and lon is not None:
            webbrowser.open(google_maps_url(lat, lon))

    def _open_apple_maps(self):
        from app.core.gps_utils import parse_decimal_input, apple_maps_url
        import webbrowser
        lat = parse_decimal_input(self._gps_lat_edit.text())
        lon = parse_decimal_input(self._gps_lon_edit.text())
        if lat is not None and lon is not None:
            webbrowser.open(apple_maps_url(lat, lon))

    # ── Public API ────────────────────────────────────────────────────────

    def populate(self, image: ImageFile):
        self._current_image = image
        if not image._loaded:
            image.load_exif()
        exif = image.exif

        for sw in self._sections.values():
            sw.populate(exif)

        # GPS extra tab
        lat = exif.get("_GPSLatDecimal")
        lon = exif.get("_GPSLonDecimal")
        if lat is not None:
            self._gps_lat_edit.setText(f"{lat:.6f}")
        if lon is not None:
            self._gps_lon_edit.setText(f"{lon:.6f}")
        if lat is not None and lon is not None:
            self._gps_dms_label.setText(
                f"{format_dms(lat, True)}\n{format_dms(lon, False)}"
            )
        alt_raw = exif.get("GPSAltitude")
        if alt_raw:
            if isinstance(alt_raw, float):
                self._gps_alt_edit.setText(f"{alt_raw:.1f}")
            elif isinstance(alt_raw, (list, tuple)) and len(alt_raw) == 2:
                self._gps_alt_edit.setText(f"{alt_raw[0]/max(alt_raw[1],1):.1f}")

        # All-fields table
        self._populate_all_table(exif)

        # Reset state
        self._pending_changes.clear()
        self._btn_save.setEnabled(False)
        self._btn_revert.setEnabled(False)
        self._dirty_label.setText("")

        # Mark modified fields if image is dirty
        for key in image.modified_keys:
            self.exif_changed.emit({key: str(exif.get(key, ""))})

    def _populate_all_table(self, exif: Dict[str, Any]):
        rows = [(k, v) for k, v in sorted(exif.items()) if not k.startswith("_")]
        self._all_table.setRowCount(len(rows))
        for i, (k, v) in enumerate(rows):
            self._all_table.setItem(i, 0, QTableWidgetItem(k))
            self._all_table.setItem(i, 1, QTableWidgetItem(str(v)[:120]))

    def clear(self):
        self._current_image = None
        for sw in self._sections.values():
            sw.clear()
        self._gps_lat_edit.clear()
        self._gps_lon_edit.clear()
        self._gps_alt_edit.clear()
        self._gps_dms_label.setText("")
        self._all_table.setRowCount(0)
        self._pending_changes.clear()
        self._btn_save.setEnabled(False)
        self._btn_revert.setEnabled(False)
        self._dirty_label.setText("")

    def collect_all_changes(self) -> Dict[str, str]:
        """Collect changes from all section widgets."""
        changes = {}
        for sw in self._sections.values():
            changes.update(sw.collect())
        changes.update(self._pending_changes)
        return changes
