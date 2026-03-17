"""
rename_dialog.py — Mosko Photo Labs
Batch rename images based on EXIF-aware filename patterns.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QFormLayout, QMessageBox, QSpinBox, QComboBox
)

from app.models.image_model import ImageCollection


_TOKENS = {
    "{date}":       "YYYYMMDD from DateTimeOriginal",
    "{time}":       "HHMMSS from DateTimeOriginal",
    "{year}":       "4-digit year",
    "{month}":      "2-digit month",
    "{day}":        "2-digit day",
    "{camera}":     "Camera model (spaces → _)",
    "{lens}":       "Lens model (spaces → _)",
    "{seq}":        "Auto-increment sequence number",
    "{original}":   "Original filename (no extension)",
}


def _expand_token(token: str, image, seq: int, pad: int) -> str:
    from app.models.image_model import ImageFile
    exif = image.exif

    def _clean(s: str) -> str:
        s = re.sub(r"[\\/:*?\"<>|]", "", s)
        return s.replace(" ", "_")

    dt_str = exif.get("DateTimeOriginal") or exif.get("DateTime") or ""
    # EXIF datetime: "2024:07:14 16:30:00"
    try:
        dt_parts = dt_str.replace(":", "").replace(" ", "")  # "20240714163000"
        date_part = dt_parts[:8]  # "20240714"
        time_part = dt_parts[8:14]  # "163000"
    except Exception:
        date_part = "00000000"
        time_part = "000000"

    replacements = {
        "{date}":     date_part,
        "{time}":     time_part,
        "{year}":     date_part[:4],
        "{month}":    date_part[4:6],
        "{day}":      date_part[6:8],
        "{camera}":   _clean(exif.get("Model", "Unknown")),
        "{lens}":     _clean(exif.get("LensModel", "UnknownLens")),
        "{seq}":      str(seq).zfill(pad),
        "{original}": image.stem,
    }
    return replacements.get(token, token)


def build_new_name(pattern: str, image, seq: int, pad: int) -> str:
    """Expand all tokens in a pattern for a given image."""
    result = pattern
    for token in _TOKENS:
        if token in result:
            result = result.replace(token, _expand_token(token, image, seq, pad))
    return result + image.extension


class RenameDialog(QDialog):
    def __init__(self, collection: ImageCollection, parent=None):
        super().__init__(parent)
        self._collection = collection
        self.setWindowTitle("Batch Rename")
        self.setMinimumSize(680, 520)
        self._build_ui()
        self._refresh_preview()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        # Pattern input
        pat_grp = QGroupBox("Filename Pattern")
        pat_layout = QFormLayout(pat_grp)
        pat_layout.setSpacing(8)

        self._pattern_edit = QLineEdit("{date}_{camera}_{seq}")
        self._pattern_edit.textChanged.connect(self._refresh_preview)
        lbl_pat = QLabel("Pattern:")
        lbl_pat.setObjectName("FieldLabel")
        pat_layout.addRow(lbl_pat, self._pattern_edit)

        self._seq_spin = QSpinBox()
        self._seq_spin.setRange(1, 99999)
        self._seq_spin.setValue(1)
        self._seq_spin.valueChanged.connect(self._refresh_preview)
        lbl_seq = QLabel("Start #:")
        lbl_seq.setObjectName("FieldLabel")
        pat_layout.addRow(lbl_seq, self._seq_spin)

        self._pad_spin = QSpinBox()
        self._pad_spin.setRange(1, 6)
        self._pad_spin.setValue(3)
        self._pad_spin.valueChanged.connect(self._refresh_preview)
        lbl_pad = QLabel("Seq digits:")
        lbl_pad.setObjectName("FieldLabel")
        pat_layout.addRow(lbl_pad, self._pad_spin)

        outer.addWidget(pat_grp)

        # Token reference
        tokens_lbl = QLabel(
            "Tokens: " + "  ".join(f"<b>{k}</b>" for k in _TOKENS)
        )
        tokens_lbl.setObjectName("CameraInfo")
        tokens_lbl.setTextFormat(Qt.TextFormat.RichText)
        tokens_lbl.setWordWrap(True)
        outer.addWidget(tokens_lbl)

        # Preview table
        lbl_prev = QLabel("PREVIEW")
        lbl_prev.setObjectName("SectionHeader")
        outer.addWidget(lbl_prev)

        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Original Name", "New Name"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        outer.addWidget(self._table, 1)

        # Scope selector
        scope_row = QHBoxLayout()
        scope_row.addWidget(QLabel("Rename:"))
        self._scope_combo = QComboBox()
        self._scope_combo.addItems(["Selected images", "All images"])
        self._scope_combo.currentIndexChanged.connect(self._refresh_preview)
        scope_row.addWidget(self._scope_combo)
        scope_row.addStretch()
        outer.addLayout(scope_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_rename = QPushButton("Rename Files")
        btn_rename.setObjectName("AccentButton")
        btn_rename.clicked.connect(self._do_rename)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_rename)
        outer.addLayout(btn_row)

    def _target_images(self):
        if self._scope_combo.currentIndex() == 0:
            imgs = self._collection.selected_images
            return imgs if imgs else list(self._collection)
        return list(self._collection)

    def _refresh_preview(self):
        images = self._target_images()
        pattern = self._pattern_edit.text()
        start = self._seq_spin.value()
        pad = self._pad_spin.value()

        self._table.setRowCount(len(images))
        for i, img in enumerate(images):
            if not img._loaded:
                img.load_exif()
            new_name = build_new_name(pattern, img, start + i, pad)
            self._table.setItem(i, 0, QTableWidgetItem(img.filename))
            item = QTableWidgetItem(new_name)
            if new_name == img.filename:
                item.setForeground(self._table.palette().text())
            else:
                from app.constants import COLORS
                from PySide6.QtGui import QColor
                item.setForeground(QColor(COLORS["accent_light"]))
            self._table.setItem(i, 1, item)

    def _do_rename(self):
        images = self._target_images()
        pattern = self._pattern_edit.text()
        start = self._seq_spin.value()
        pad = self._pad_spin.value()

        renamed, errors = 0, []
        for i, img in enumerate(images):
            if not img._loaded:
                img.load_exif()
            new_name = build_new_name(pattern, img, start + i, pad)
            if new_name == img.filename:
                continue
            new_path = img.filepath.parent / new_name
            if new_path.exists():
                errors.append(f"{new_name} already exists — skipped")
                continue
            try:
                img.filepath.rename(new_path)
                img.filepath = new_path
                renamed += 1
            except OSError as e:
                errors.append(str(e))

        msg = f"Renamed {renamed} file{'s' if renamed != 1 else ''}."
        if errors:
            msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:5])
        QMessageBox.information(self, "Rename Complete", msg)
        self.accept()
