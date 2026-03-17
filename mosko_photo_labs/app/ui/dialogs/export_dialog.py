"""
export_dialog.py — Mosko Photo Labs
Export EXIF data from all (or selected) images to CSV or JSON.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QCheckBox, QGroupBox, QFormLayout,
    QMessageBox, QRadioButton, QButtonGroup
)

from app.models.image_model import ImageCollection, ImageFile


class ExportDialog(QDialog):
    def __init__(self, collection: ImageCollection, parent=None):
        super().__init__(parent)
        self._collection = collection
        self.setWindowTitle("Export EXIF Data")
        self.setFixedSize(420, 320)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # Scope
        scope_grp = QGroupBox("Images to Export")
        scope_layout = QVBoxLayout(scope_grp)
        self._scope_all = QRadioButton(
            f"All images ({len(self._collection)})"
        )
        n_sel = self._collection.selection_count
        self._scope_sel = QRadioButton(
            f"Selected images ({n_sel})"
        )
        self._scope_sel.setEnabled(n_sel > 0)
        self._scope_all.setChecked(True)
        scope_layout.addWidget(self._scope_all)
        scope_layout.addWidget(self._scope_sel)
        outer.addWidget(scope_grp)

        # Format
        fmt_grp = QGroupBox("Export Format")
        fmt_layout = QVBoxLayout(fmt_grp)
        self._fmt_csv  = QRadioButton("CSV (spreadsheet)")
        self._fmt_json = QRadioButton("JSON")
        self._fmt_csv.setChecked(True)
        fmt_layout.addWidget(self._fmt_csv)
        fmt_layout.addWidget(self._fmt_json)
        outer.addWidget(fmt_grp)

        # Options
        self._skip_empty = QCheckBox("Skip fields with empty values")
        self._skip_empty.setChecked(True)
        self._include_path = QCheckBox("Include full file path")
        self._include_path.setChecked(True)
        outer.addWidget(self._skip_empty)
        outer.addWidget(self._include_path)

        outer.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_export = QPushButton("Export…")
        btn_export.setObjectName("AccentButton")
        btn_export.clicked.connect(self._do_export)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_export)
        outer.addLayout(btn_row)

    def _target_images(self) -> List[ImageFile]:
        if self._scope_sel.isChecked():
            return self._collection.selected_images or list(self._collection)
        return list(self._collection)

    def _do_export(self):
        fmt = "csv" if self._fmt_csv.isChecked() else "json"
        ext_filter = "CSV Files (*.csv)" if fmt == "csv" else "JSON Files (*.json)"
        default_name = f"mosko_exif_export.{fmt}"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export EXIF Data", default_name, ext_filter
        )
        if not filepath:
            return

        images = self._target_images()
        # Ensure EXIF is loaded
        for img in images:
            if not img._loaded:
                img.load_exif()

        skip_empty = self._skip_empty.isChecked()
        inc_path   = self._include_path.isChecked()

        rows = []
        all_keys = set()
        for img in images:
            row = {}
            if inc_path:
                row["_filepath"] = str(img.filepath)
            row["_filename"] = img.filename
            for k, v in img.exif.items():
                if k.startswith("_") and k not in ("_filepath", "_filename"):
                    continue
                if skip_empty and (v == "" or v is None):
                    continue
                row[k] = str(v)
            rows.append(row)
            all_keys.update(row.keys())

        try:
            if fmt == "csv":
                all_keys_sorted = sorted(all_keys)
                with open(filepath, "w", newline="", encoding="utf-8") as fh:
                    writer = csv.DictWriter(fh, fieldnames=all_keys_sorted,
                                            extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(rows)
            else:
                with open(filepath, "w", encoding="utf-8") as fh:
                    json.dump(rows, fh, indent=2, ensure_ascii=False)

            QMessageBox.information(
                self, "Export Complete",
                f"Exported EXIF data for {len(images)} image{'s' if len(images) != 1 else ''}\n"
                f"to: {filepath}"
            )
            self.accept()

        except OSError as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
