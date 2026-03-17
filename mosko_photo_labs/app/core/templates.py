"""
templates.py — Mosko Photo Labs
EXIF preset template management: save, load, apply, delete.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExifTemplate:
    name: str
    description: str = ""
    fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "fields": self.fields,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ExifTemplate":
        return cls(
            name=d.get("name", "Unnamed"),
            description=d.get("description", ""),
            fields=d.get("fields", {}),
        )


class TemplateManager:
    """Persist and query EXIF templates on disk as JSON."""

    def __init__(self, filepath: Optional[Path] = None):
        if filepath is None:
            filepath = Path.home() / "mosko_templates.json"
        self.filepath = Path(filepath)
        self._templates: List[ExifTemplate] = []
        self.load()

    # ── Persistence ───────────────────────────────────────────────────────

    def load(self) -> None:
        """Load templates from disk (silently if missing)."""
        self._templates = []
        if not self.filepath.exists():
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for item in data.get("templates", []):
                self._templates.append(ExifTemplate.from_dict(item))
        except (json.JSONDecodeError, OSError):
            self._templates = []

    def save(self) -> None:
        """Persist templates to disk."""
        data = {"templates": [t.to_dict() for t in self._templates]}
        with open(self.filepath, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    # ── CRUD ──────────────────────────────────────────────────────────────

    @property
    def templates(self) -> List[ExifTemplate]:
        return list(self._templates)

    @property
    def names(self) -> List[str]:
        return [t.name for t in self._templates]

    def get(self, name: str) -> Optional[ExifTemplate]:
        for t in self._templates:
            if t.name == name:
                return t
        return None

    def add(self, template: ExifTemplate) -> None:
        """Add or replace a template by name."""
        self._templates = [t for t in self._templates if t.name != template.name]
        self._templates.append(template)
        self.save()

    def delete(self, name: str) -> bool:
        original = len(self._templates)
        self._templates = [t for t in self._templates if t.name != name]
        if len(self._templates) < original:
            self.save()
            return True
        return False

    def rename(self, old_name: str, new_name: str) -> bool:
        t = self.get(old_name)
        if t is None:
            return False
        t.name = new_name
        self.save()
        return True

    # ── Built-in starter templates ─────────────────────────────────────────

    def add_builtin_templates(self) -> None:
        """Seed default templates if none exist."""
        if self._templates:
            return
        defaults = [
            ExifTemplate(
                name="My Copyright",
                description="Add photographer name and copyright notice",
                fields={"Artist": "", "Copyright": ""},
            ),
            ExifTemplate(
                name="GPS — New York City",
                description="Midtown Manhattan coordinates",
                fields={
                    "GPSLatitude": 40.7580,
                    "GPSLatitudeRef": "N",
                    "GPSLongitude": -73.9855,
                    "GPSLongitudeRef": "W",
                },
            ),
            ExifTemplate(
                name="GPS — Los Angeles",
                description="Downtown Los Angeles coordinates",
                fields={
                    "GPSLatitude": 34.0522,
                    "GPSLatitudeRef": "N",
                    "GPSLongitude": -118.2437,
                    "GPSLongitudeRef": "W",
                },
            ),
            ExifTemplate(
                name="Sony 85mm f/1.4 GM",
                description="Sony FE 85mm F1.4 GM lens info",
                fields={
                    "LensMake": "Sony",
                    "LensModel": "FE 85mm F1.4 GM",
                    "FocalLength": 85.0,
                    "FocalLengthIn35mmFilm": 85,
                    "MaxApertureValue": 1.4,
                },
            ),
            ExifTemplate(
                name="Canon 50mm f/1.2L",
                description="Canon EF 50mm f/1.2L USM lens info",
                fields={
                    "LensMake": "Canon",
                    "LensModel": "EF50mm f/1.2L USM",
                    "FocalLength": 50.0,
                    "FocalLengthIn35mmFilm": 50,
                    "MaxApertureValue": 1.2,
                },
            ),
        ]
        for t in defaults:
            self._templates.append(t)
        self.save()
