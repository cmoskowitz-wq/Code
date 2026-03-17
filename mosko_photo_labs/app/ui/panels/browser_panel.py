"""
browser_panel.py — Mosko Photo Labs
Left panel: folder selector + image thumbnail grid.
Loads thumbnails in a background thread to keep UI responsive.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import (
    Qt, QThread, Signal, QRunnable, QThreadPool, QObject, Slot
)
from PySide6.QtGui import QPixmap, QImage, QFont, QPainter, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QSizePolicy,
    QFrame, QComboBox, QLineEdit, QAbstractItemView
)

from app.constants import COLORS, SUPPORTED_EXTENSIONS, THUMB_SMALL
from app.models.image_model import ImageCollection, ImageFile


# ── Thumbnail loader (background) ─────────────────────────────────────────

class _ThumbSignals(QObject):
    done = Signal(str, bytes)   # filepath, png_bytes


class _ThumbLoader(QRunnable):
    def __init__(self, filepath: str, size: tuple):
        super().__init__()
        self.filepath = filepath
        self.size = size
        self.signals = _ThumbSignals()

    def run(self):
        from app.core.exif_engine import get_thumbnail
        data = get_thumbnail(self.filepath, self.size)
        if data:
            self.signals.done.emit(self.filepath, data)


# ── Browser Panel ──────────────────────────────────────────────────────────

class BrowserPanel(QFrame):
    """
    Left panel: folder navigation + scrollable thumbnail grid.
    Emits image_selected(ImageFile) when a thumbnail is clicked.
    """

    image_selected    = Signal(object)   # ImageFile
    selection_changed = Signal(list)     # List[ImageFile]
    folder_loaded     = Signal(int)      # count

    THUMB_SIZE = 96

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BrowserPanel")
        self.setMinimumWidth(220)
        self.setMaximumWidth(320)

        self._collection: Optional[ImageCollection] = None
        self._current_index: int = -1
        self._pool = QThreadPool.globalInstance()
        self._thumb_cache: dict[str, QPixmap] = {}

        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title
        title = QLabel("LIBRARY")
        title.setObjectName("SectionHeader")
        layout.addWidget(title)

        # Folder row
        folder_row = QHBoxLayout()
        self._folder_label = QLabel("No folder")
        self._folder_label.setObjectName("CameraInfo")
        self._folder_label.setWordWrap(True)
        folder_row.addWidget(self._folder_label, 1)
        btn_open = QPushButton("Open")
        btn_open.setFixedWidth(56)
        btn_open.setToolTip("Open a folder of images")
        btn_open.clicked.connect(self._pick_folder)
        folder_row.addWidget(btn_open)
        layout.addLayout(folder_row)

        # Filter / sort row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Filter...")
        self._filter_edit.setClearButtonEnabled(True)
        self._filter_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter_edit, 1)
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["Name", "Date", "Size", "Type"])
        self._sort_combo.setFixedWidth(70)
        self._sort_combo.currentTextChanged.connect(self._apply_sort)
        filter_row.addWidget(self._sort_combo)
        layout.addLayout(filter_row)

        # Stats label
        self._stats_label = QLabel("")
        self._stats_label.setObjectName("CameraInfo")
        layout.addWidget(self._stats_label)

        # Thumbnail list
        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(self._list.iconSize().__class__(self.THUMB_SIZE, self.THUMB_SIZE))
        self._list.setGridSize(self._list.gridSize().__class__(self.THUMB_SIZE + 16, self.THUMB_SIZE + 28))
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setMovement(QListWidget.Movement.Static)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._list.setUniformItemSizes(True)
        self._list.setWrapping(True)
        self._list.setWordWrap(True)
        self._list.setSpacing(4)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list, 1)

        # Bottom select-all / none row
        sel_row = QHBoxLayout()
        btn_all  = QPushButton("All")
        btn_none = QPushButton("None")
        for b in (btn_all, btn_none):
            b.setFixedHeight(24)
            sel_row.addWidget(b)
        btn_all.clicked.connect(self._select_all)
        btn_none.clicked.connect(self._select_none)
        layout.addLayout(sel_row)

    # ── Folder loading ────────────────────────────────────────────────────

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Image Folder",
                                                   str(Path.home() / "Pictures"))
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder: str):
        col = ImageCollection()
        count = col.load_folder(folder)
        self._collection = col

        folder_path = Path(folder)
        self._folder_label.setText(folder_path.name)
        self._folder_label.setToolTip(str(folder_path))
        self._stats_label.setText(f"{count} image{'s' if count != 1 else ''}")

        self._populate_list()
        self.folder_loaded.emit(count)

    def _populate_list(self):
        self._list.clear()
        self._thumb_cache.clear()
        if self._collection is None:
            return
        filter_text = self._filter_edit.text().lower()
        for img in self._collection:
            if filter_text and filter_text not in img.filename.lower():
                continue
            item = QListWidgetItem(img.filename)
            item.setData(Qt.ItemDataRole.UserRole, img)
            item.setSizeHint(self._list.gridSize())
            # Placeholder pixmap
            item.setIcon(self._placeholder_icon(img.filename))
            self._list.addItem(item)
            # Kick off background thumb load
            self._schedule_thumb(img)

    def _schedule_thumb(self, img: ImageFile):
        loader = _ThumbLoader(str(img.filepath), (self.THUMB_SIZE, self.THUMB_SIZE))
        loader.signals.done.connect(self._on_thumb_ready)
        self._pool.start(loader)

    @Slot(str, bytes)
    def _on_thumb_ready(self, filepath: str, data: bytes):
        pix = QPixmap()
        pix.loadFromData(data)
        if pix.isNull():
            return
        self._thumb_cache[filepath] = pix
        # Find matching list item and update icon
        for i in range(self._list.count()):
            item = self._list.item(i)
            img: ImageFile = item.data(Qt.ItemDataRole.UserRole)
            if img and str(img.filepath) == filepath:
                from PySide6.QtGui import QIcon
                item.setIcon(QIcon(pix))
                break

    def _placeholder_icon(self, filename: str) -> object:
        from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
        ext = Path(filename).suffix.lower()
        pix = QPixmap(self.THUMB_SIZE, self.THUMB_SIZE)
        pix.fill(QColor(COLORS["bg_card"]))
        painter = QPainter(pix)
        painter.setPen(QColor(COLORS["text_secondary"]))
        painter.setFont(QFont("Arial", 9))
        label = ext.upper().lstrip(".") or "IMG"
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, label)
        painter.end()
        return QIcon(pix)

    # ── Selection ─────────────────────────────────────────────────────────

    def _on_selection_changed(self):
        selected = [item.data(Qt.ItemDataRole.UserRole)
                    for item in self._list.selectedItems()
                    if item.data(Qt.ItemDataRole.UserRole)]
        if selected:
            self.image_selected.emit(selected[0])
            self.selection_changed.emit(selected)
        if self._collection:
            self._collection.clear_selection()
            for item in self._list.selectedItems():
                img: ImageFile = item.data(Qt.ItemDataRole.UserRole)
                if img:
                    idx = self._collection.index_of(img)
                    self._collection.select(idx)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        img: ImageFile = item.data(Qt.ItemDataRole.UserRole)
        if img:
            self.image_selected.emit(img)

    def _select_all(self):
        self._list.selectAll()

    def _select_none(self):
        self._list.clearSelection()

    # ── Filter / Sort ─────────────────────────────────────────────────────

    def _apply_filter(self, text: str):
        for i in range(self._list.count()):
            item = self._list.item(i)
            img: ImageFile = item.data(Qt.ItemDataRole.UserRole)
            match = not text or text.lower() in (img.filename.lower() if img else "")
            item.setHidden(not match)

    def _apply_sort(self, sort_key: str):
        if self._collection is None:
            return
        key_map = {"Name": "filename", "Date": "date",
                   "Size": "size", "Type": "extension"}
        self._collection.sort(key_map.get(sort_key, "filename"))
        self._populate_list()

    # ── Public API ────────────────────────────────────────────────────────

    def collection(self) -> Optional[ImageCollection]:
        return self._collection

    def navigate(self, delta: int) -> Optional[ImageFile]:
        """Move selection by delta (-1 prev, +1 next). Returns new image."""
        if self._list.count() == 0:
            return None
        current_row = self._list.currentRow()
        new_row = max(0, min(self._list.count() - 1, current_row + delta))
        self._list.setCurrentRow(new_row)
        item = self._list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def mark_dirty(self, filepath: str):
        """Add a ● indicator to a modified item."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            img: ImageFile = item.data(Qt.ItemDataRole.UserRole)
            if img and str(img.filepath) == filepath:
                if not item.text().startswith("●"):
                    item.setText("● " + img.filename)
                item.setForeground(QColor(COLORS["modified"]))
                break

    def unmark_dirty(self, filepath: str):
        for i in range(self._list.count()):
            item = self._list.item(i)
            img: ImageFile = item.data(Qt.ItemDataRole.UserRole)
            if img and str(img.filepath) == filepath:
                item.setText(img.filename)
                item.setForeground(QColor(COLORS["text_primary"]))
                break
