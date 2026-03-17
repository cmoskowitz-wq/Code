"""
conftest.py — Mosko Photo Labs tests
Shared fixtures: in-memory test JPEG images with known EXIF.
"""

from __future__ import annotations

import io
import os
import struct
import tempfile
from pathlib import Path
from typing import Generator

import piexif
import pytest
from PIL import Image


def _make_test_jpeg(
    tmp_path: Path,
    filename: str = "test.jpg",
    make: str = "TestCamera",
    model: str = "TC-100",
    date_original: str = "2024:07:14 16:30:00",
    iso: int = 400,
    focal_length: tuple = (50, 1),
    gps_lat: tuple | None = None,
    gps_lon: tuple | None = None,
    artist: str = "Test Photographer",
    copyright_: str = "© 2024 Test",
) -> Path:
    """Create a small JPEG with embedded EXIF in tmp_path."""
    # Create a tiny RGB image
    img = Image.new("RGB", (64, 64), color=(100, 120, 140))

    # Build EXIF
    exif_dict: dict = {
        "0th": {
            piexif.ImageIFD.Make:      make.encode() + b"\x00",
            piexif.ImageIFD.Model:     model.encode() + b"\x00",
            piexif.ImageIFD.Software:  b"MoskoTest\x00",
            piexif.ImageIFD.DateTime:  date_original.encode() + b"\x00",
            piexif.ImageIFD.Artist:    artist.encode() + b"\x00",
            piexif.ImageIFD.Copyright: copyright_.encode() + b"\x00",
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: date_original.encode() + b"\x00",
            piexif.ExifIFD.ISOSpeedRatings:  iso,
            piexif.ExifIFD.FocalLength:       focal_length,
            piexif.ExifIFD.FNumber:           (18, 10),   # f/1.8
            piexif.ExifIFD.ExposureTime:      (1, 500),   # 1/500s
        },
        "GPS": {},
        "1st": {},
        "thumbnail": None,
    }

    if gps_lat is not None and gps_lon is not None:
        lat_val = gps_lat
        lon_val = gps_lon
        exif_dict["GPS"] = {
            piexif.GPSIFD.GPSLatitudeRef:  b"N",
            piexif.GPSIFD.GPSLatitude:     lat_val,
            piexif.GPSIFD.GPSLongitudeRef: b"W",
            piexif.GPSIFD.GPSLongitude:    lon_val,
            piexif.GPSIFD.GPSAltitude:     (500, 1),
            piexif.GPSIFD.GPSAltitudeRef:  0,
        }

    exif_bytes = piexif.dump(exif_dict)
    filepath = tmp_path / filename
    img.save(str(filepath), format="JPEG", exif=exif_bytes)
    return filepath


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def jpeg_file(tmp_path: Path) -> Path:
    """A basic JPEG with EXIF."""
    return _make_test_jpeg(tmp_path)


@pytest.fixture
def jpeg_with_gps(tmp_path: Path) -> Path:
    """A JPEG with GPS data (40°45′N 73°59′W ≈ NYC)."""
    return _make_test_jpeg(
        tmp_path,
        filename="gps_test.jpg",
        gps_lat=((40, 1), (45, 1), (0, 1)),
        gps_lon=((73, 1), (59, 1), (0, 1)),
    )


@pytest.fixture
def jpeg_no_exif(tmp_path: Path) -> Path:
    """A JPEG with no EXIF at all."""
    img = Image.new("RGB", (64, 64), color=(50, 50, 50))
    filepath = tmp_path / "no_exif.jpg"
    img.save(str(filepath), format="JPEG")
    return filepath


@pytest.fixture
def folder_with_images(tmp_path: Path) -> Path:
    """A folder containing 5 JPEG test images."""
    for i in range(5):
        _make_test_jpeg(
            tmp_path,
            filename=f"image_{i:03d}.jpg",
            make="Nikon",
            model=f"Z{i+1}",
            iso=100 * (i + 1),
            artist="Test Photographer",
        )
    return tmp_path


@pytest.fixture
def template_manager(tmp_path: Path):
    """A TemplateManager using a temp file."""
    from app.core.templates import TemplateManager
    return TemplateManager(tmp_path / "test_templates.json")
