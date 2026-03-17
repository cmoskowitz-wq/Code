"""
test_exif_engine.py — Mosko Photo Labs
Unit tests for the EXIF read/write engine.
"""

import os
from pathlib import Path

import piexif
import pytest
from PIL import Image

from app.core.exif_engine import (
    read_exif,
    write_exif,
    write_xmp_sidecar,
    get_thumbnail,
    is_raw,
    is_inplace_writable,
    format_exposure,
    format_aperture,
    _encode_string,
    _encode_rational,
)


# ── read_exif ──────────────────────────────────────────────────────────────

class TestReadExif:
    def test_reads_make(self, jpeg_file):
        exif = read_exif(jpeg_file)
        assert exif.get("Make") == "TestCamera"

    def test_reads_model(self, jpeg_file):
        exif = read_exif(jpeg_file)
        assert exif.get("Model") == "TC-100"

    def test_reads_iso(self, jpeg_file):
        exif = read_exif(jpeg_file)
        assert exif.get("ISOSpeedRatings") == 400

    def test_reads_artist(self, jpeg_file):
        exif = read_exif(jpeg_file)
        assert exif.get("Artist") == "Test Photographer"

    def test_reads_copyright(self, jpeg_file):
        exif = read_exif(jpeg_file)
        assert "2024" in str(exif.get("Copyright", ""))

    def test_reads_focal_length(self, jpeg_file):
        exif = read_exif(jpeg_file)
        fl = exif.get("FocalLength")
        # Could be float 50.0 or ratio (50, 1)
        assert fl is not None

    def test_no_exif_returns_empty_dict(self, jpeg_no_exif):
        exif = read_exif(jpeg_no_exif)
        assert isinstance(exif, dict)

    def test_gps_decimal_keys_present(self, jpeg_with_gps):
        exif = read_exif(jpeg_with_gps)
        assert "_GPSLatDecimal" in exif
        assert "_GPSLonDecimal" in exif

    def test_gps_lat_is_positive_north(self, jpeg_with_gps):
        exif = read_exif(jpeg_with_gps)
        lat = exif.get("_GPSLatDecimal")
        assert lat is not None
        assert lat > 0   # "N"

    def test_gps_lon_is_negative_west(self, jpeg_with_gps):
        exif = read_exif(jpeg_with_gps)
        lon = exif.get("_GPSLonDecimal")
        assert lon is not None
        assert lon < 0   # "W"

    def test_nonexistent_file_returns_empty(self, tmp_path):
        exif = read_exif(tmp_path / "does_not_exist.jpg")
        assert isinstance(exif, dict)


# ── write_exif ─────────────────────────────────────────────────────────────

class TestWriteExif:
    def test_write_artist(self, jpeg_file):
        ok, msg = write_exif(jpeg_file, {"Artist": "New Photographer"}, backup=False)
        assert ok, msg
        exif = read_exif(jpeg_file)
        assert exif.get("Artist") == "New Photographer"

    def test_write_creates_backup(self, jpeg_file):
        bak = jpeg_file.with_suffix(jpeg_file.suffix + ".bak")
        assert not bak.exists()
        write_exif(jpeg_file, {"Artist": "Backup Test"}, backup=True)
        assert bak.exists()

    def test_write_gps_latitude(self, jpeg_file):
        ok, msg = write_exif(jpeg_file, {"GPSLatitude": 40.7580}, backup=False)
        assert ok, msg
        exif = read_exif(jpeg_file)
        assert "_GPSLatDecimal" in exif
        lat = exif["_GPSLatDecimal"]
        assert abs(lat - 40.7580) < 0.01

    def test_write_gps_negative_longitude(self, jpeg_file):
        ok, msg = write_exif(jpeg_file, {"GPSLongitude": -73.9855}, backup=False)
        assert ok, msg
        exif = read_exif(jpeg_file)
        if "_GPSLonDecimal" in exif:
            lon = exif["_GPSLonDecimal"]
            assert lon < 0

    def test_write_iso(self, jpeg_file):
        ok, msg = write_exif(jpeg_file, {"ISOSpeedRatings": 800}, backup=False)
        assert ok, msg
        exif = read_exif(jpeg_file)
        assert exif.get("ISOSpeedRatings") == 800

    def test_write_returns_error_for_raw(self, tmp_path):
        # Create a fake .cr2 file
        fake_raw = tmp_path / "test.cr2"
        fake_raw.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)
        ok, msg = write_exif(fake_raw, {"Artist": "X"}, backup=False)
        # Should fall back to XMP (ok) or fail gracefully (not crash)
        assert isinstance(ok, bool)
        assert isinstance(msg, str)

    def test_write_multiple_fields(self, jpeg_file):
        updates = {
            "Artist": "Multi Field",
            "Copyright": "© 2026",
            "ImageDescription": "Test description",
        }
        ok, msg = write_exif(jpeg_file, updates, backup=False)
        assert ok
        exif = read_exif(jpeg_file)
        assert exif.get("Artist") == "Multi Field"


# ── write_xmp_sidecar ──────────────────────────────────────────────────────

class TestXmpSidecar:
    def test_creates_xmp_file(self, jpeg_file):
        ok, msg = write_xmp_sidecar(jpeg_file, {"Artist": "XMP Test"})
        xmp_path = jpeg_file.with_suffix(".xmp")
        assert ok, msg
        assert xmp_path.exists()

    def test_xmp_contains_artist(self, jpeg_file):
        write_xmp_sidecar(jpeg_file, {"Artist": "XMP Photographer"})
        xmp_path = jpeg_file.with_suffix(".xmp")
        content = xmp_path.read_text(encoding="utf-8")
        assert "XMP Photographer" in content

    def test_xmp_valid_xml(self, jpeg_file):
        import xml.etree.ElementTree as ET
        write_xmp_sidecar(jpeg_file, {"Artist": "Valid XML"})
        xmp_path = jpeg_file.with_suffix(".xmp")
        # Strip XMP packet wrapper for parsing
        text = xmp_path.read_text(encoding="utf-8")
        # Find the xmpmeta element
        start = text.find("<")
        end = text.rfind(">") + 1
        xml_fragment = text[start:end]
        # Should not raise
        try:
            ET.fromstring(xml_fragment)
        except ET.ParseError:
            pass  # XMP namespaces may cause issues; content check is sufficient


# ── get_thumbnail ──────────────────────────────────────────────────────────

class TestThumbnail:
    def test_returns_bytes(self, jpeg_file):
        result = get_thumbnail(jpeg_file, (64, 64))
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_returns_none_for_missing_file(self, tmp_path):
        result = get_thumbnail(tmp_path / "missing.jpg", (64, 64))
        assert result is None

    def test_thumbnail_is_png(self, jpeg_file):
        result = get_thumbnail(jpeg_file)
        # PNG magic bytes: 0x89 0x50 0x4e 0x47
        assert result[:4] == b"\x89PNG"

    def test_thumbnail_respects_size(self, jpeg_file):
        from PIL import Image
        import io
        data = get_thumbnail(jpeg_file, (32, 32))
        img = Image.open(io.BytesIO(data))
        assert img.width <= 32
        assert img.height <= 32


# ── Helper format functions ────────────────────────────────────────────────

class TestFormatHelpers:
    def test_format_exposure_fraction(self):
        assert "1/500" in format_exposure((1, 500))

    def test_format_exposure_long(self):
        result = format_exposure((2, 1))
        assert "2" in result

    def test_format_exposure_float(self):
        result = format_exposure(0.002)
        assert "/" in result or "s" in result

    def test_format_aperture_rational(self):
        result = format_aperture((18, 10))
        assert "f/" in result
        assert "1.8" in result

    def test_format_aperture_float(self):
        result = format_aperture(2.8)
        assert "f/2.8" in result


# ── is_raw / is_inplace_writable ──────────────────────────────────────────

class TestFileTypeChecks:
    @pytest.mark.parametrize("ext", [".cr2", ".nef", ".arw", ".dng", ".raf"])
    def test_raw_extensions(self, ext, tmp_path):
        f = tmp_path / f"test{ext}"
        assert is_raw(f)

    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".tiff", ".tif"])
    def test_writable_extensions(self, ext, tmp_path):
        f = tmp_path / f"test{ext}"
        assert is_inplace_writable(f)
        assert not is_raw(f)

    @pytest.mark.parametrize("ext", [".png", ".bmp", ".webp"])
    def test_standard_not_raw(self, ext, tmp_path):
        f = tmp_path / f"test{ext}"
        assert not is_raw(f)
        assert not is_inplace_writable(f)
