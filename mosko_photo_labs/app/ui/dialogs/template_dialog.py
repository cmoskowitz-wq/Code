"""
template_dialog.py — Mosko Photo Labs
Manage, create, and apply EXIF templates.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QDialogButtonBox, QGroupBox, QFormLayout, QMessageBox,
    QSplitter, QWidget
)

from app.constants import COLORS
from app.core.templates import TemplateManager, ExifTemplate
from app.models.image_model import ImageCollection


class TemplateDialog(QDialog):
    """
    Dialog for managing EXIF templates.
    - Left: list of templates
    - Right: template details + edit
    - Apply: stamp template onto selected images
    """

    template_applied = Signal(dict)   # {field: value}

    def __init__(self, manager: TemplateManager,
                 collection: Optional[ImageCollection] = None,
                 parent=None):
        super().__init__(parent)
        self._manager = manager
        self._collection = collection
        self._selected_template: Optional[ExifTemplate] = None

        self.setWindowTitle("EXIF Templates")
        self.setMinimumSize(600, 480)
        self._build_ui()
        self._refresh_list()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: template list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        lbl = QLabel("TEMPLATES")
        lbl.setObjectName("SectionHeader")
        left_layout.addWidget(lbl)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_template_selected)
        left_layout.addWidget(self._list, 1)

        btn_row = QHBoxLayout()
        btn_new = QPushButton("New")
        btn_del = QPushButton("Delete")
        btn_del.setObjectName("DangerButton")
        btn_new.clicked.connect(self._new_template)
        btn_del.clicked.connect(self._delete_template)
        btn_row.addWidget(btn_new)
        btn_row.addWidget(btn_del)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left)

        # Right: edit panel
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(8)
        lbl_name = QLabel("Name:")
        lbl_name.setObjectName("FieldLabel")
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Template name…")
        form.addRow(lbl_name, self._name_edit)

        lbl_desc = QLabel("Description:")
        lbl_desc.setObjectName("FieldLabel")
        self._desc_edit = QLineEdit()
        self._desc_edit.setPlaceholderText("Optional description…")
        form.addRow(lbl_desc, self._desc_edit)
        right_layout.addLayout(form)

        # Fields JSON editor
        lbl_fields = QLabel("FIELDS (key: value, one per line)")
        lbl_fields.setObjectName("SectionHeader")
        right_layout.addWidget(lbl_fields)

        self._fields_edit = QTextEdit()
        self._fields_edit.setPlaceholderText(
            "Artist: Jane Doe\n"
            "Copyright: © 2026 Jane Doe\n"
            "GPSLatitude: 40.7580\n"
            "GPSLongitude: -73.9855"
        )
        self._fields_edit.setFont(
            self._fields_edit.font().__class__("Courier New", 11)
        )
        right_layout.addWidget(self._fields_edit, 1)

        save_row = QHBoxLayout()
        btn_save_t = QPushButton("Save Template")
        btn_save_t.setObjectName("AccentButton")
        btn_save_t.clicked.connect(self._save_template)
        save_row.addStretch()
        save_row.addWidget(btn_save_t)
        right_layout.addLayout(save_row)

        splitter.addWidget(right)
        splitter.setSizes([200, 400])
        outer.addWidget(splitter, 1)

        # Apply section
        apply_grp = QGroupBox("Apply Template")
        apply_layout = QHBoxLayout(apply_grp)
        apply_layout.setSpacing(10)

        n = self._collection.selection_count if self._collection else 0
        apply_info = QLabel(
            f"Apply to {n} selected image{'s' if n != 1 else ''}  "
            if n > 0 else "No images selected. "
        )
        apply_info.setObjectName("CameraInfo")
        apply_layout.addWidget(apply_info, 1)

        btn_apply = QPushButton("Apply to Selection")
        btn_apply.setObjectName("AccentButton")
        btn_apply.clicked.connect(self._apply_to_selection)
        apply_layout.addWidget(btn_apply)

        btn_apply_all = QPushButton("Apply to All")
        btn_apply_all.clicked.connect(self._apply_to_all)
        apply_layout.addWidget(btn_apply_all)

        outer.addWidget(apply_grp)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()
        btn_row2.addWidget(close_btn)
        outer.addLayout(btn_row2)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _refresh_list(self):
        self._list.clear()
        for t in self._manager.templates:
            item = QListWidgetItem(t.name)
            item.setData(Qt.ItemDataRole.UserRole, t)
            self._list.addItem(item)

    def _on_template_selected(self, current: QListWidgetItem, _prev):
        if current is None:
            return
        t: ExifTemplate = current.data(Qt.ItemDataRole.UserRole)
        if t is None:
            return
        self._selected_template = t
        self._name_edit.setText(t.name)
        self._desc_edit.setText(t.description)
        lines = "\n".join(f"{k}: {v}" for k, v in t.fields.items())
        self._fields_edit.setPlainText(lines)

    def _parse_fields(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for line in self._fields_edit.toPlainText().splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                if key:
                    # Try numeric
                    try:
                        result[key] = float(val) if "." in val else int(val)
                    except ValueError:
                        result[key] = val
        return result

    def _new_template(self):
        self._list.clearSelection()
        self._selected_template = None
        self._name_edit.clear()
        self._desc_edit.clear()
        self._fields_edit.clear()
        self._name_edit.setFocus()

    def _save_template(self):
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter a template name.")
            return
        t = ExifTemplate(
            name=name,
            description=self._desc_edit.text().strip(),
            fields=self._parse_fields(),
        )
        self._manager.add(t)
        self._refresh_list()
        # Re-select the saved item
        for i in range(self._list.count()):
            if self._list.item(i).text() == name:
                self._list.setCurrentRow(i)
                break

    def _delete_template(self):
        item = self._list.currentItem()
        if item is None:
            return
        name = item.text()
        reply = QMessageBox.question(
            self, "Delete Template",
            f"Delete template '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._manager.delete(name)
            self._refresh_list()
            self._new_template()

    def _apply_to_selection(self):
        if self._selected_template is None:
            QMessageBox.information(self, "No Template", "Select a template first.")
            return
        if self._collection is None or self._collection.selection_count == 0:
            QMessageBox.information(self, "No Selection", "Select images first.")
            return
        count = self._collection.apply_to_selection(self._selected_template.fields)
        self.template_applied.emit(self._selected_template.fields)
        QMessageBox.information(
            self, "Template Applied",
            f"Applied '{self._selected_template.name}' to {count} image{'s' if count != 1 else ''}."
        )

    def _apply_to_all(self):
        if self._selected_template is None:
            QMessageBox.information(self, "No Template", "Select a template first.")
            return
        if self._collection is None or len(self._collection) == 0:
            return
        count = self._collection.apply_to_all(self._selected_template.fields)
        self.template_applied.emit(self._selected_template.fields)
        QMessageBox.information(
            self, "Template Applied",
            f"Applied '{self._selected_template.name}' to all {count} images."
        )
