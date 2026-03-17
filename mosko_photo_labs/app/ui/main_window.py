"""
main_window.py — Mosko Photo Labs
Main application window: menu bar, toolbar, three-panel layout, status bar.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QSettings, QTimer, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon, QFont, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QStatusBar,
    QToolBar, QLabel, QMessageBox, QFileDialog, QProgressBar,
    QApplication
)

from app.constants import APP_NAME, APP_VERSION, APP_TAGLINE, MAX_RECENT_FOLDERS
from app.core.templates import TemplateManager
from app.models.image_model import ImageCollection, ImageFile
from app.ui.panels.browser_panel import BrowserPanel
from app.ui.panels.preview_panel import PreviewPanel
from app.ui.panels.exif_panel import ExifPanel


class MainWindow(QMainWindow):
    """Mosko Photo Labs main application window."""

    def __init__(self):
        super().__init__()
        self._collection: Optional[ImageCollection] = None
        self._current_image: Optional[ImageFile] = None
        self._template_manager = TemplateManager()
        self._template_manager.add_builtin_templates()
        self._recent_folders: List[str] = []
        self._settings = QSettings("MoskoPhotoLabs", "MoskoPhotoLabs")

        self.setWindowTitle(f"{APP_NAME} — {APP_TAGLINE}")
        self.setMinimumSize(1100, 700)
        self.resize(1400, 900)

        self._build_ui()
        self._build_menu()
        self._build_toolbar()
        self._build_statusbar()
        self._connect_signals()
        self._load_settings()
        self._show_welcome()

    # ── UI Construction ────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(1)

        self._browser = BrowserPanel()
        self._preview = PreviewPanel()
        self._exif_panel = ExifPanel()

        self._splitter.addWidget(self._browser)
        self._splitter.addWidget(self._preview)
        self._splitter.addWidget(self._exif_panel)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)
        self._splitter.setSizes([250, 800, 340])

        layout.addWidget(self._splitter)

    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        act_open = QAction("&Open Folder…", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._open_folder)
        file_menu.addAction(act_open)

        self._recent_menu = file_menu.addMenu("Recent Folders")

        file_menu.addSeparator()

        act_save = QAction("&Save Current Image", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._save_current)
        file_menu.addAction(act_save)

        act_save_all = QAction("Save &All Modified", self)
        act_save_all.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_all.triggered.connect(self._save_all)
        file_menu.addAction(act_save_all)

        act_revert = QAction("&Revert Changes", self)
        act_revert.setShortcut(QKeySequence("Ctrl+Z"))
        act_revert.triggered.connect(self._revert_current)
        file_menu.addAction(act_revert)

        file_menu.addSeparator()

        act_export = QAction("&Export EXIF Data…", self)
        act_export.triggered.connect(self._export_exif)
        file_menu.addAction(act_export)

        file_menu.addSeparator()

        act_quit = QAction("&Quit", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Edit
        edit_menu = mb.addMenu("&Edit")

        act_bulk = QAction("&Bulk Edit Selected…", self)
        act_bulk.setShortcut(QKeySequence("Ctrl+B"))
        act_bulk.triggered.connect(self._bulk_edit)
        edit_menu.addAction(act_bulk)

        act_copy_exif = QAction("&Copy EXIF from Current to Selection…", self)
        act_copy_exif.triggered.connect(self._copy_exif_to_selection)
        edit_menu.addAction(act_copy_exif)

        edit_menu.addSeparator()

        act_templates = QAction("&Templates…", self)
        act_templates.setShortcut(QKeySequence("Ctrl+T"))
        act_templates.triggered.connect(self._open_templates)
        edit_menu.addAction(act_templates)

        act_rename = QAction("Batch &Rename…", self)
        act_rename.triggered.connect(self._batch_rename)
        edit_menu.addAction(act_rename)

        # Navigate
        nav_menu = mb.addMenu("&Navigate")

        act_prev = QAction("&Previous Image", self)
        act_prev.setShortcut(QKeySequence(Qt.Key.Key_Left))
        act_prev.triggered.connect(self._prev_image)
        nav_menu.addAction(act_prev)

        act_next = QAction("&Next Image", self)
        act_next.setShortcut(QKeySequence(Qt.Key.Key_Right))
        act_next.triggered.connect(self._next_image)
        nav_menu.addAction(act_next)

        nav_menu.addSeparator()

        act_sel_all = QAction("Select &All", self)
        act_sel_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        act_sel_all.triggered.connect(lambda: self._browser._select_all())
        nav_menu.addAction(act_sel_all)

        act_sel_none = QAction("Select &None", self)
        act_sel_none.setShortcut(QKeySequence("Escape"))
        act_sel_none.triggered.connect(lambda: self._browser._select_none())
        nav_menu.addAction(act_sel_none)

        # View
        view_menu = mb.addMenu("&View")

        act_toggle_browser = QAction("Toggle &Browser Panel", self)
        act_toggle_browser.setShortcut(QKeySequence("Ctrl+1"))
        act_toggle_browser.triggered.connect(
            lambda: self._browser.setVisible(not self._browser.isVisible())
        )
        view_menu.addAction(act_toggle_browser)

        act_toggle_exif = QAction("Toggle &EXIF Panel", self)
        act_toggle_exif.setShortcut(QKeySequence("Ctrl+2"))
        act_toggle_exif.triggered.connect(
            lambda: self._exif_panel.setVisible(not self._exif_panel.isVisible())
        )
        view_menu.addAction(act_toggle_exif)

        # Help
        help_menu = mb.addMenu("&Help")
        act_about = QAction(f"About {APP_NAME}", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _build_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setIconSize(QSize(16, 16))
        tb.setMovable(False)
        self.addToolBar(tb)

        tb.addAction("📂  Open Folder", self._open_folder)
        tb.addSeparator()
        tb.addAction("💾  Save", self._save_current)
        tb.addAction("💾  Save All", self._save_all)
        tb.addSeparator()
        tb.addAction("✏️  Bulk Edit", self._bulk_edit)
        tb.addAction("📋  Templates", self._open_templates)
        tb.addAction("🔤  Rename", self._batch_rename)
        tb.addSeparator()
        tb.addAction("◀  Prev", self._prev_image)
        tb.addAction("Next  ▶", self._next_image)
        tb.addSeparator()
        tb.addAction("📊  Export EXIF", self._export_exif)
        tb.addSeparator()

        # Stats label in toolbar
        self._toolbar_stats = QLabel("   No folder open")
        self._toolbar_stats.setObjectName("CameraInfo")
        tb.addWidget(self._toolbar_stats)

    def _build_statusbar(self):
        sb = self.statusBar()

        self._status_label = QLabel("Ready — Mosko Photo Labs")
        sb.addWidget(self._status_label, 1)

        self._status_image = QLabel("")
        sb.addPermanentWidget(self._status_image)

        self._status_sel = QLabel("")
        sb.addPermanentWidget(self._status_sel)

        self._progress = QProgressBar()
        self._progress.setFixedWidth(150)
        self._progress.setVisible(False)
        sb.addPermanentWidget(self._progress)

    # ── Signal wiring ──────────────────────────────────────────────────────

    def _connect_signals(self):
        self._browser.image_selected.connect(self._on_image_selected)
        self._browser.selection_changed.connect(self._on_selection_changed)
        self._browser.folder_loaded.connect(self._on_folder_loaded)

        self._preview.prev_requested.connect(self._prev_image)
        self._preview.next_requested.connect(self._next_image)

        self._exif_panel.save_requested.connect(self._save_current)
        self._exif_panel.revert_requested.connect(self._revert_current)
        self._exif_panel.exif_changed.connect(self._on_exif_changed)

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_folder_loaded(self, count: int):
        self._collection = self._browser.collection()
        self._toolbar_stats.setText(
            f"   {count} image{'s' if count != 1 else ''}"
        )
        self._status_label.setText(
            f"Opened {count} image{'s' if count != 1 else ''} — "
            f"{self._collection.folder.name if self._collection and self._collection.folder else ''}"
        )
        if self._collection and self._collection.folder:
            self._add_recent(str(self._collection.folder))

    def _on_image_selected(self, image: ImageFile):
        self._current_image = image
        if not image._loaded:
            image.load_exif()
        self._preview.show_image(image)
        self._exif_panel.populate(image)
        raw_tag = " [RAW]" if image.is_raw else ""
        gps_tag = " 📍" if image.has_gps else ""
        self._status_image.setText(
            f"{image.filename}{raw_tag}{gps_tag}  {image.size_mb:.1f} MB"
        )

    def _on_selection_changed(self, images: list):
        n = len(images)
        self._status_sel.setText(
            f"  {n} selected" if n > 0 else ""
        )

    def _on_exif_changed(self, updates: dict):
        if self._current_image:
            self._browser.mark_dirty(str(self._current_image.filepath))
            self._status_label.setText(
                f"Modified: {self._current_image.filename} — unsaved changes"
            )

    # ── File operations ────────────────────────────────────────────────────

    def _open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Open Image Folder",
            self._recent_folders[0] if self._recent_folders else str(Path.home())
        )
        if folder:
            self._browser.load_folder(folder)

    def _save_current(self):
        if self._current_image is None:
            self._status_label.setText("No image selected.")
            return
        if not self._current_image.is_dirty:
            self._status_label.setText("No changes to save.")
            return
        ok, msg = self._current_image.save()
        self._status_label.setText(msg)
        if ok:
            self._browser.unmark_dirty(str(self._current_image.filepath))

    def _save_all(self):
        if self._collection is None:
            return
        dirty = self._collection.dirty_images
        if not dirty:
            self._status_label.setText("No unsaved changes.")
            return
        saved, errors, msgs = self._collection.save_all_dirty()
        msg = f"Saved {saved} image{'s' if saved != 1 else ''}."
        if errors:
            msg += f"  {errors} error{'s' if errors > 1 else ''}."
        self._status_label.setText(msg)
        for img in dirty:
            if not img.is_dirty:
                self._browser.unmark_dirty(str(img.filepath))

    def _revert_current(self):
        if self._current_image is None:
            return
        self._current_image.revert()
        self._exif_panel.populate(self._current_image)
        self._browser.unmark_dirty(str(self._current_image.filepath))
        self._status_label.setText(f"Reverted: {self._current_image.filename}")

    # ── Navigation ─────────────────────────────────────────────────────────

    def _prev_image(self):
        img = self._browser.navigate(-1)
        if img:
            self._on_image_selected(img)

    def _next_image(self):
        img = self._browser.navigate(1)
        if img:
            self._on_image_selected(img)

    # ── Edit operations ────────────────────────────────────────────────────

    def _bulk_edit(self):
        if self._collection is None:
            QMessageBox.information(self, "No Folder", "Open a folder first.")
            return
        if self._collection.selection_count == 0:
            QMessageBox.information(self, "No Selection",
                                     "Select one or more images first (Ctrl+A for all).")
            return
        from app.ui.dialogs.bulk_editor import BulkEditorDialog
        dlg = BulkEditorDialog(self._collection, self)
        dlg.exec()
        self._status_label.setText(
            f"Bulk edit applied to {self._collection.selection_count} images — use Save All to write."
        )

    def _copy_exif_to_selection(self):
        if self._current_image is None or self._collection is None:
            return
        if self._collection.selection_count == 0:
            QMessageBox.information(self, "No Selection", "Select target images first.")
            return
        src_exif = {k: v for k, v in self._current_image.exif.items()
                    if not k.startswith("_")}
        count = self._collection.apply_to_selection(src_exif)
        self._status_label.setText(
            f"Copied EXIF from {self._current_image.filename} to {count} images."
        )

    def _open_templates(self):
        from app.ui.dialogs.template_dialog import TemplateDialog
        dlg = TemplateDialog(self._template_manager, self._collection, self)
        dlg.template_applied.connect(self._on_template_applied)
        dlg.exec()

    def _on_template_applied(self, fields: dict):
        if self._current_image:
            self._exif_panel.populate(self._current_image)

    def _batch_rename(self):
        if self._collection is None or len(self._collection) == 0:
            QMessageBox.information(self, "No Images", "Open a folder with images first.")
            return
        from app.ui.dialogs.rename_dialog import RenameDialog
        dlg = RenameDialog(self._collection, self)
        if dlg.exec():
            self._browser.load_folder(str(self._collection.folder))

    def _export_exif(self):
        if self._collection is None or len(self._collection) == 0:
            QMessageBox.information(self, "No Images", "Open a folder with images first.")
            return
        from app.ui.dialogs.export_dialog import ExportDialog
        dlg = ExportDialog(self._collection, self)
        dlg.exec()

    # ── Recent folders ─────────────────────────────────────────────────────

    def _add_recent(self, folder: str):
        if folder in self._recent_folders:
            self._recent_folders.remove(folder)
        self._recent_folders.insert(0, folder)
        self._recent_folders = self._recent_folders[:MAX_RECENT_FOLDERS]
        self._rebuild_recent_menu()
        self._save_settings()

    def _rebuild_recent_menu(self):
        self._recent_menu.clear()
        for folder in self._recent_folders:
            path = Path(folder)
            act = QAction(path.name, self)
            act.setToolTip(folder)
            act.setData(folder)
            act.triggered.connect(lambda checked, f=folder: self._browser.load_folder(f))
            self._recent_menu.addAction(act)
        if not self._recent_folders:
            placeholder = QAction("(none)", self)
            placeholder.setEnabled(False)
            self._recent_menu.addAction(placeholder)

    # ── Settings ───────────────────────────────────────────────────────────

    def _save_settings(self):
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("splitter", self._splitter.saveState())
        self._settings.setValue("recent_folders",
                                 json.dumps(self._recent_folders))

    def _load_settings(self):
        geom = self._settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        sp = self._settings.value("splitter")
        if sp:
            self._splitter.restoreState(sp)
        raw = self._settings.value("recent_folders", "[]")
        try:
            self._recent_folders = json.loads(raw)
        except Exception:
            self._recent_folders = []
        self._rebuild_recent_menu()

    def closeEvent(self, event):
        # Warn about unsaved changes
        dirty = self._collection.dirty_images if self._collection else []
        if dirty:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"You have unsaved changes in {len(dirty)} image{'s' if len(dirty) > 1 else ''}.\n"
                "Save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_all()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        self._save_settings()
        super().closeEvent(event)

    # ── Welcome / About ────────────────────────────────────────────────────

    def _show_welcome(self):
        self._status_label.setText(
            f"Welcome to {APP_NAME} {APP_VERSION}  —  "
            "Open a folder of images to get started (Ctrl+O)"
        )

    def _show_about(self):
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h2>{APP_NAME}</h2>"
            f"<p><em>{APP_TAGLINE}</em></p>"
            f"<p>Version {APP_VERSION}</p>"
            "<p>Professional EXIF editor for photographers.<br>"
            "Read, edit, and batch-update metadata on JPEG, TIFF, PNG, "
            "and all major RAW formats.</p>"
            "<hr>"
            "<p>Supports: Canon CR2/CR3, Nikon NEF, Sony ARW, Adobe DNG, "
            "Fujifilm RAF, Olympus ORF, Panasonic RW2, and more.</p>"
            "<p>XMP sidecar files are written for RAW formats, "
            "in-place EXIF editing for JPEG/TIFF.</p>"
        )
