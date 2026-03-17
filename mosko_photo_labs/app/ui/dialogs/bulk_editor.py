"""
bulk_editor.py — Mosko Photo Labs
Dialog for bulk/batch editing EXIF fields on multiple selected images.
"""

from __future__ import annotations

from typing import Dict, List, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QScrollArea, QWidget, QFormLayout,
    QFrame, QDialogButtonBox, QComboBox, QGroupBox, QMessageBox
)

from app.constants import COLORS, EXIF_SECTIONS, EXIF_CHOICES
from app.models.image_model import ImageCollection


class _BulkField(QWidget):
    """One row in the bulk editor: enable checkbox + label + input."""

    def __init__(self, key: str, label: str, value_type: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.value_type = value_type

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        self._check = QCheckBox()
        self._check.setFixedWidth(18)
        self._check.stateChanged.connect(self._toggle_enabled)
        layout.addWidget(self._check)

        lbl = QLabel(label + ":")
        lbl.setObjectName("FieldLabel")
        lbl.setFixedWidth(140)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lbl)

        if value_type == "choice" and key in EXIF_CHOICES:
            self._input = QComboBox()
            for k, v in EXIF_CHOICES[key].items():
                self._input.addItem(v, k)
        else:
            self._input = QLineEdit()
            self._input.setPlaceholderText("Enter value…")

        self._input.setEnabled(False)
        layout.addWidget(self._input, 1)

    def _toggle_enabled(self, state: int):
        self._input.setEnabled(state == Qt.CheckState.Checked.value)

    @property
    def is_enabled(self) -> bool:
        return self._check.isChecked()

    def value(self) -> str:
        if isinstance(self._input, QComboBox):
            return str(self._input.currentData())
        return self._input.text().strip()

    def set_value(self, v: str):
        if isinstance(self._input, QLineEdit):
            self._input.setText(v)

    def enable(self, checked: bool = True):
        self._check.setChecked(checked)


class BulkEditorDialog(QDialog):
    """
    Modal dialog to apply EXIF field updates to a set of images.
    User ticks the fields they want to change, enters values, then
    confirms to stage the changes (images are not saved to disk here).
    """

    def __init__(self, collection: ImageCollection, parent=None):
        super().__init__(parent)
        self._collection = collection
        self.setWindowTitle("Bulk EXIF Editor")
        self.setMinimumSize(560, 640)
        self._fields: Dict[str, _BulkField] = {}
        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        # Header
        n = self._collection.selection_count
        header = QLabel(
            f"Bulk edit {n} selected image{'s' if n != 1 else ''}.\n"
            "Tick a field to override it on all selected images."
        )
        header.setObjectName("CameraInfo")
        header.setWordWrap(True)
        outer.addWidget(header)

        # Scroll area with all sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(4, 4, 4, 4)
        container_layout.setSpacing(6)

        for section_name, fields in EXIF_SECTIONS.items():
            # Skip read-only fields (editable=False)
            editable_fields = [(k, lbl, ifd, tag, vt, ed)
                               for k, lbl, ifd, tag, vt, ed in fields if ed]
            if not editable_fields:
                continue

            grp = QGroupBox(section_name)
            grp_layout = QVBoxLayout(grp)
            grp_layout.setContentsMargins(8, 8, 8, 8)
            grp_layout.setSpacing(2)

            for key, label, _ifd, _tag, vtype, _ed in editable_fields:
                bf = _BulkField(key, label, vtype)
                self._fields[key] = bf
                grp_layout.addWidget(bf)

            container_layout.addWidget(grp)

        container_layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

        # GPS quick-set
        gps_grp = QGroupBox("Quick GPS Set")
        gps_layout = QFormLayout(gps_grp)
        gps_layout.setSpacing(6)
        self._lat_edit = QLineEdit()
        self._lat_edit.setPlaceholderText("40.7580 or 40.7580 N")
        self._lon_edit = QLineEdit()
        self._lon_edit.setPlaceholderText("-73.9855 or 73.9855 W")
        lbl_lat = QLabel("Latitude:")
        lbl_lat.setObjectName("FieldLabel")
        lbl_lon = QLabel("Longitude:")
        lbl_lon.setObjectName("FieldLabel")
        gps_layout.addRow(lbl_lat, self._lat_edit)
        gps_layout.addRow(lbl_lon, self._lon_edit)
        outer.addWidget(gps_grp)

        # Buttons
        btn_box = QDialogButtonBox()
        btn_apply = QPushButton("Apply to Selection")
        btn_apply.setObjectName("AccentButton")
        btn_cancel = QPushButton("Cancel")
        btn_box.addButton(btn_apply, QDialogButtonBox.ButtonRole.AcceptRole)
        btn_box.addButton(btn_cancel, QDialogButtonBox.ButtonRole.RejectRole)
        btn_apply.clicked.connect(self._apply)
        btn_cancel.clicked.connect(self.reject)
        outer.addWidget(btn_box)

    # ── Logic ─────────────────────────────────────────────────────────────

    def _apply(self):
        updates: Dict[str, Any] = {}

        # Collect enabled fields
        for key, bf in self._fields.items():
            if bf.is_enabled and bf.value():
                updates[key] = bf.value()

        # GPS
        from app.core.gps_utils import parse_decimal_input
        lat_text = self._lat_edit.text().strip()
        lon_text = self._lon_edit.text().strip()
        if lat_text and lon_text:
            lat = parse_decimal_input(lat_text)
            lon = parse_decimal_input(lon_text)
            if lat is not None and lon is not None:
                updates["GPSLatitude"]     = lat
                updates["GPSLongitude"]    = lon
                updates["_GPSLatDecimal"]  = lat
                updates["_GPSLonDecimal"]  = lon

        if not updates:
            QMessageBox.information(self, "No Fields Selected",
                                    "Tick at least one field to apply.")
            return

        count = self._collection.apply_to_selection(updates)
        self.accept()
        QMessageBox.information(
            self, "Bulk Edit Applied",
            f"Staged {len(updates)} field change{'s' if len(updates) != 1 else ''} "
            f"on {count} image{'s' if count != 1 else ''}.\n\n"
            "Use File → Save All to write changes to disk."
        )

    def applied_updates(self) -> Dict[str, Any]:
        """Return the staged updates after the dialog is accepted."""
        return {}   # applied in-dialog via apply_to_selection
