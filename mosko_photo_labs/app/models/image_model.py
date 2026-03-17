"""
image_model.py — Mosko Photo Labs
ImageFile and ImageCollection data models with change tracking.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set

from app.core.exif_engine import read_exif, write_exif, write_xmp_sidecar, is_raw


class ImageFile:
    """
    Represents a single image on disk, with its EXIF data and
    a change log for undo/redo support.
    """

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._exif_original: Dict[str, Any] = {}
        self._exif_current:  Dict[str, Any] = {}
        self._thumbnail: Optional[bytes] = None
        self._loaded = False
        self._thumbnail_loaded = False

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def filename(self) -> str:
        return self.filepath.name

    @property
    def stem(self) -> str:
        return self.filepath.stem

    @property
    def extension(self) -> str:
        return self.filepath.suffix.lower()

    @property
    def is_raw(self) -> bool:
        return is_raw(self.filepath)

    @property
    def size_mb(self) -> float:
        try:
            return self.filepath.stat().st_size / 1_048_576
        except OSError:
            return 0.0

    @property
    def exif(self) -> Dict[str, Any]:
        return self._exif_current

    @property
    def thumbnail(self) -> Optional[bytes]:
        return self._thumbnail

    @property
    def is_dirty(self) -> bool:
        return self._exif_current != self._exif_original

    @property
    def modified_keys(self) -> Set[str]:
        all_keys = set(self._exif_original) | set(self._exif_current)
        return {k for k in all_keys if self._exif_original.get(k) != self._exif_current.get(k)}

    # ── Loading ───────────────────────────────────────────────────────────

    def load_exif(self) -> None:
        """Read EXIF from disk. Called lazily."""
        self._exif_original = read_exif(self.filepath)
        self._exif_current  = copy.deepcopy(self._exif_original)
        self._loaded = True

    def load_thumbnail(self, size=(160, 160)) -> None:
        """Render and cache thumbnail bytes."""
        from app.core.exif_engine import get_thumbnail
        self._thumbnail = get_thumbnail(self.filepath, size)
        self._thumbnail_loaded = True

    # ── Editing ───────────────────────────────────────────────────────────

    def set_field(self, key: str, value: Any) -> None:
        self._exif_current[key] = value

    def set_fields(self, updates: Dict[str, Any]) -> None:
        self._exif_current.update(updates)

    def get_field(self, key: str, default: Any = None) -> Any:
        return self._exif_current.get(key, default)

    def revert(self) -> None:
        """Discard unsaved changes."""
        self._exif_current = copy.deepcopy(self._exif_original)

    # ── Saving ────────────────────────────────────────────────────────────

    def save(self, backup: bool = True) -> tuple[bool, str]:
        """Write modified EXIF back to disk (or XMP sidecar for RAW)."""
        if not self.is_dirty:
            return True, "No changes to save."

        changes = {k: self._exif_current[k] for k in self.modified_keys}

        if self.is_raw:
            ok, msg = write_xmp_sidecar(self.filepath, changes)
        else:
            ok, msg = write_exif(self.filepath, changes, backup=backup)

        if ok:
            self._exif_original = copy.deepcopy(self._exif_current)

        return ok, msg

    # ── Display helpers ───────────────────────────────────────────────────

    @property
    def camera_summary(self) -> str:
        make  = self._exif_current.get("Make", "")
        model = self._exif_current.get("Model", "")
        if model:
            return model if make in model else f"{make} {model}".strip()
        return make or "Unknown Camera"

    @property
    def has_gps(self) -> bool:
        return "_GPSLatDecimal" in self._exif_current or "GPSLatitude" in self._exif_current

    @property
    def datetime_original(self) -> Optional[str]:
        return self._exif_current.get("DateTimeOriginal") or self._exif_current.get("DateTime")

    def __repr__(self) -> str:
        return f"<ImageFile {self.filename} dirty={self.is_dirty}>"


# ── ImageCollection ────────────────────────────────────────────────────────

class ImageCollection:
    """
    Manages a flat list of ImageFile objects from a folder.
    Supports filter, sort, selection, and bulk edit operations.
    """

    SORT_FILENAME  = "filename"
    SORT_DATE      = "date"
    SORT_SIZE      = "size"
    SORT_EXTENSION = "extension"

    def __init__(self):
        self._images: List[ImageFile] = []
        self._folder: Optional[Path] = None
        self._selected: Set[int] = set()

    # ── Loading ───────────────────────────────────────────────────────────

    def load_folder(self, folder: str | Path, extensions=None) -> int:
        """
        Populate the collection from a directory.
        Returns the number of images found.
        """
        from app.constants import SUPPORTED_EXTENSIONS
        folder = Path(folder)
        if not folder.is_dir():
            return 0

        exts = extensions or SUPPORTED_EXTENSIONS
        files = sorted(
            (p for p in folder.iterdir()
             if p.is_file() and p.suffix.lower() in exts),
            key=lambda p: p.name.lower(),
        )

        self._images = [ImageFile(f) for f in files]
        self._folder = folder
        self._selected.clear()
        return len(self._images)

    # ── Access ────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._images)

    def __iter__(self) -> Iterator[ImageFile]:
        return iter(self._images)

    def __getitem__(self, index: int) -> ImageFile:
        return self._images[index]

    def index_of(self, image: ImageFile) -> int:
        return self._images.index(image)

    @property
    def folder(self) -> Optional[Path]:
        return self._folder

    @property
    def images(self) -> List[ImageFile]:
        return list(self._images)

    @property
    def dirty_images(self) -> List[ImageFile]:
        return [img for img in self._images if img.is_dirty]

    # ── Selection ─────────────────────────────────────────────────────────

    def select(self, index: int) -> None:
        self._selected.add(index)

    def deselect(self, index: int) -> None:
        self._selected.discard(index)

    def toggle_select(self, index: int) -> None:
        if index in self._selected:
            self._selected.discard(index)
        else:
            self._selected.add(index)

    def select_all(self) -> None:
        self._selected = set(range(len(self._images)))

    def clear_selection(self) -> None:
        self._selected.clear()

    @property
    def selected_indices(self) -> List[int]:
        return sorted(self._selected)

    @property
    def selected_images(self) -> List[ImageFile]:
        return [self._images[i] for i in sorted(self._selected) if i < len(self._images)]

    @property
    def selection_count(self) -> int:
        return len(self._selected)

    # ── Bulk operations ───────────────────────────────────────────────────

    def apply_to_selection(self, updates: Dict[str, Any]) -> int:
        """Apply EXIF updates to all selected images. Returns count updated."""
        count = 0
        for img in self.selected_images:
            if not img._loaded:
                img.load_exif()
            img.set_fields(updates)
            count += 1
        return count

    def apply_to_all(self, updates: Dict[str, Any]) -> int:
        """Apply EXIF updates to all images in the collection."""
        for img in self._images:
            if not img._loaded:
                img.load_exif()
            img.set_fields(updates)
        return len(self._images)

    def save_all_dirty(self, backup: bool = True) -> tuple[int, int, list[str]]:
        """
        Save all dirty images.
        Returns (saved_count, error_count, error_messages).
        """
        saved, errors, msgs = 0, 0, []
        for img in self._images:
            if img.is_dirty:
                ok, msg = img.save(backup=backup)
                if ok:
                    saved += 1
                else:
                    errors += 1
                    msgs.append(msg)
        return saved, errors, msgs

    def revert_all(self) -> None:
        for img in self._images:
            img.revert()

    # ── Sort ──────────────────────────────────────────────────────────────

    def sort(self, key: str = SORT_FILENAME, reverse: bool = False) -> None:
        if key == self.SORT_FILENAME:
            self._images.sort(key=lambda i: i.filename.lower(), reverse=reverse)
        elif key == self.SORT_DATE:
            self._images.sort(key=lambda i: i.datetime_original or "", reverse=reverse)
        elif key == self.SORT_SIZE:
            self._images.sort(key=lambda i: i.size_mb, reverse=reverse)
        elif key == self.SORT_EXTENSION:
            self._images.sort(key=lambda i: i.extension, reverse=reverse)
        self._selected.clear()

    # ── Statistics ────────────────────────────────────────────────────────

    def statistics(self) -> Dict[str, Any]:
        """Return aggregate stats about this collection."""
        from collections import Counter
        loaded = [img for img in self._images if img._loaded]
        cameras   = Counter(img.camera_summary for img in loaded)
        lenses    = Counter(img.get_field("LensModel", "Unknown") for img in loaded)
        has_gps   = sum(1 for img in loaded if img.has_gps)
        raw_count = sum(1 for img in self._images if img.is_raw)
        return {
            "total":     len(self._images),
            "raw":       raw_count,
            "has_gps":   has_gps,
            "cameras":   dict(cameras.most_common(10)),
            "lenses":    dict(lenses.most_common(10)),
        }
