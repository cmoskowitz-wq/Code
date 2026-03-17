"""
exif_engine.py — Mosko Photo Labs
Core EXIF read/write engine supporting JPEG, TIFF, PNG, and RAW formats.

Write strategy:
  - JPEG / TIFF  → in-place via piexif (with .bak backup)
  - All others   → XMP sidecar file (industry standard for RAW)
"""

from __future__ import annotations

import copy
import io
import os
import struct
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import piexif
from PIL import Image

from app.constants import INPLACE_WRITABLE, RAW_EXTENSIONS
from app.core.gps_utils import (
    decimal_to_piexif_gps,
    piexif_gps_to_decimal,
    piexif_rational_to_float,
)


# ── piexif tag lookup ──────────────────────────────────────────────────────

_IFD_MAP = {
    "0th":  piexif.ImageIFD,
    "Exif": piexif.ExifIFD,
    "GPS":  piexif.GPSIFD,
    "1st":  piexif.ImageIFD,
}

# Build reverse map: tag_name → (ifd_key, tag_id)
_TAG_LOOKUP: Dict[str, Tuple[str, int]] = {}
for _ifd_key, _ifd_cls in _IFD_MAP.items():
    for _attr in dir(_ifd_cls):
        if not _attr.startswith("_"):
            _tag_id = getattr(_ifd_cls, _attr)
            if isinstance(_tag_id, int) and _attr not in _TAG_LOOKUP:
                _TAG_LOOKUP[_attr] = (_ifd_key, _tag_id)


def _get_ifd_key(field_name: str) -> Optional[Tuple[str, int]]:
    """Return (ifd_key, tag_id) for a field name, or None."""
    return _TAG_LOOKUP.get(field_name)


# ── Raw bytes → display value ──────────────────────────────────────────────

def _decode_value(tag_name: str, raw_value: Any) -> Any:
    """Convert piexif raw values to human-friendly Python types."""
    if isinstance(raw_value, bytes):
        # Strip null terminator, decode
        try:
            return raw_value.rstrip(b"\x00").decode("utf-8", errors="replace")
        except Exception:
            return raw_value.hex()
    if isinstance(raw_value, tuple) and len(raw_value) == 2:
        num, den = raw_value
        if den == 0:
            return 0.0
        return num / den
    if isinstance(raw_value, (list, tuple)):
        return raw_value  # GPS tuples, lens info, etc.
    return raw_value


def _encode_string(value: str) -> bytes:
    return value.encode("utf-8") + b"\x00"


def _encode_rational(value: float) -> Tuple[int, int]:
    # Store as integer / 10000 to preserve 4 decimal places
    return (int(round(value * 10000)), 10000)


# ── Read ───────────────────────────────────────────────────────────────────

def read_exif(filepath: str | Path) -> Dict[str, Any]:
    """
    Read EXIF from any supported file.
    Returns a flat dict: {field_name: python_value}.
    """
    filepath = Path(filepath)
    ext = filepath.suffix.lower()

    exif_dict: Dict[str, Any] = {}

    # ── piexif path (JPEG/TIFF + PNG) ──────────────────────────────────
    if ext in INPLACE_WRITABLE or ext == ".png":
        try:
            raw = piexif.load(str(filepath))
            for ifd_key, ifd_data in raw.items():
                if not isinstance(ifd_data, dict):
                    continue
                ifd_cls = _IFD_MAP.get(ifd_key)
                if ifd_cls is None:
                    continue
                # Build reverse map for this ifd
                rev = {getattr(ifd_cls, a): a for a in dir(ifd_cls)
                       if not a.startswith("_") and isinstance(getattr(ifd_cls, a), int)}
                for tag_id, raw_val in ifd_data.items():
                    tag_name = rev.get(tag_id, f"Tag_{tag_id}")
                    exif_dict[tag_name] = _decode_value(tag_name, raw_val)
        except Exception:
            pass

    # ── exifread path (all formats, great for RAW) ─────────────────────
    try:
        import exifread
        with open(filepath, "rb") as fh:
            tags = exifread.process_file(fh, details=False, stop_tag="EOF")
        for tag_key, tag_val in tags.items():
            # Normalise key: "EXIF FocalLength" → "FocalLength"
            parts = tag_key.split(" ", 1)
            name = parts[-1].replace(" ", "") if len(parts) > 1 else tag_key
            # Only fill if piexif didn't already find it
            if name not in exif_dict:
                exif_dict[name] = str(tag_val)
    except Exception:
        pass

    # ── GPS decimal convenience keys ──────────────────────────────────
    try:
        lat_raw = piexif.load(str(filepath))["GPS"].get(piexif.GPSIFD.GPSLatitude)
        lat_ref = piexif.load(str(filepath))["GPS"].get(piexif.GPSIFD.GPSLatitudeRef, b"N")
        lon_raw = piexif.load(str(filepath))["GPS"].get(piexif.GPSIFD.GPSLongitude)
        lon_ref = piexif.load(str(filepath))["GPS"].get(piexif.GPSIFD.GPSLongitudeRef, b"E")
        if lat_raw:
            exif_dict["_GPSLatDecimal"] = piexif_gps_to_decimal(lat_raw, lat_ref)
        if lon_raw:
            exif_dict["_GPSLonDecimal"] = piexif_gps_to_decimal(lon_raw, lon_ref)
    except Exception:
        pass

    return exif_dict


# ── Write ──────────────────────────────────────────────────────────────────

def write_exif(filepath: str | Path, updates: Dict[str, Any],
               backup: bool = True) -> Tuple[bool, str]:
    """
    Write EXIF updates to JPEG/TIFF in-place.
    Returns (success, message).
    """
    filepath = Path(filepath)
    ext = filepath.suffix.lower()

    if ext not in INPLACE_WRITABLE:
        # Fallback to XMP sidecar for non-writable formats
        return write_xmp_sidecar(filepath, updates)

    try:
        # Load existing EXIF (or start fresh)
        try:
            exif_bytes = piexif.load(str(filepath))
        except Exception:
            exif_bytes = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        # Apply updates
        for field_name, value in updates.items():
            if field_name.startswith("_"):
                continue  # skip internal keys
            _apply_field(exif_bytes, field_name, value)

        # Backup original
        if backup:
            bak_path = filepath.with_suffix(filepath.suffix + ".bak")
            if not bak_path.exists():
                import shutil
                shutil.copy2(filepath, bak_path)

        # Write
        new_bytes = piexif.dump(exif_bytes)
        piexif.insert(new_bytes, str(filepath))
        return True, f"Saved {filepath.name}"

    except Exception as exc:
        return False, f"Error writing {filepath.name}: {exc}"


def _apply_field(exif_bytes: dict, field_name: str, value: Any) -> None:
    """Encode a single field value and write it into the piexif dict."""
    lookup = _get_ifd_key(field_name)
    if lookup is None:
        return
    ifd_key, tag_id = lookup

    # GPS coordinates from decimal float
    if field_name == "GPSLatitude" and isinstance(value, float):
        exif_bytes["GPS"][piexif.GPSIFD.GPSLatitude] = decimal_to_piexif_gps(abs(value))
        exif_bytes["GPS"][piexif.GPSIFD.GPSLatitudeRef] = b"N" if value >= 0 else b"S"
        return
    if field_name == "GPSLongitude" and isinstance(value, float):
        exif_bytes["GPS"][piexif.GPSIFD.GPSLongitude] = decimal_to_piexif_gps(abs(value))
        exif_bytes["GPS"][piexif.GPSIFD.GPSLongitudeRef] = b"E" if value >= 0 else b"W"
        return
    if field_name == "GPSAltitude" and isinstance(value, (int, float)):
        alt = int(abs(float(value)) * 100)
        exif_bytes["GPS"][piexif.GPSIFD.GPSAltitude] = (alt, 100)
        exif_bytes["GPS"][piexif.GPSIFD.GPSAltitudeRef] = 0 if float(value) >= 0 else 1
        return

    # Encode by type
    if isinstance(value, str):
        encoded: Any = _encode_string(value)
    elif isinstance(value, float):
        encoded = _encode_rational(value)
    elif isinstance(value, int):
        encoded = value
    elif isinstance(value, (list, tuple)):
        encoded = value
    else:
        encoded = value

    exif_bytes[ifd_key][tag_id] = encoded


# ── XMP sidecar ────────────────────────────────────────────────────────────

_XMP_NS = {
    "x":    "adobe:ns:meta/",
    "rdf":  "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "xmp":  "http://ns.adobe.com/xap/1.0/",
    "dc":   "http://purl.org/dc/elements/1.1/",
    "exif": "http://ns.adobe.com/exif/1.0/",
    "tiff": "http://ns.adobe.com/tiff/1.0/",
}

_XMP_FIELD_MAP = {
    "Make":             ("tiff", "Make"),
    "Model":            ("tiff", "Model"),
    "Software":         ("xmp",  "CreatorTool"),
    "DateTimeOriginal": ("exif", "DateTimeOriginal"),
    "FocalLength":      ("exif", "FocalLength"),
    "LensMake":         ("exif", "LensMake"),
    "LensModel":        ("exif", "LensModel"),
    "Artist":           ("dc",   "creator"),
    "Copyright":        ("dc",   "rights"),
    "ImageDescription": ("dc",   "description"),
    "GPSLatitude":      ("exif", "GPSLatitude"),
    "GPSLongitude":     ("exif", "GPSLongitude"),
    "GPSAltitude":      ("exif", "GPSAltitude"),
}


def write_xmp_sidecar(filepath: str | Path, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Create/update an XMP sidecar file (.xmp) alongside the given image.
    Returns (success, message).
    """
    filepath = Path(filepath)
    xmp_path = filepath.with_suffix(".xmp")

    try:
        # Register all namespaces
        for prefix, uri in _XMP_NS.items():
            ET.register_namespace(prefix, uri)

        # Build minimal XMP packet
        root = ET.Element(f"{{{_XMP_NS['x']}}}xmpmeta")
        rdf = ET.SubElement(root, f"{{{_XMP_NS['rdf']}}}RDF")
        desc = ET.SubElement(rdf, f"{{{_XMP_NS['rdf']}}}Description")
        desc.set(f"{{{_XMP_NS['rdf']}}}about", "")

        for field_name, value in updates.items():
            if field_name.startswith("_") or value is None:
                continue
            mapping = _XMP_FIELD_MAP.get(field_name)
            if mapping is None:
                continue
            ns_prefix, xmp_name = mapping
            ns_uri = _XMP_NS[ns_prefix]
            desc.set(f"{{{ns_uri}}}{xmp_name}", str(value))

        tree = ET.ElementTree(root)
        with open(xmp_path, "wb") as fh:
            fh.write(b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>\n')
            tree.write(fh, encoding="utf-8", xml_declaration=False)
            fh.write(b'\n<?xpacket end="w"?>')

        return True, f"XMP sidecar saved: {xmp_path.name}"

    except Exception as exc:
        return False, f"Error writing XMP for {filepath.name}: {exc}"


# ── Thumbnail ──────────────────────────────────────────────────────────────

def get_thumbnail(filepath: str | Path, size: Tuple[int, int] = (160, 160)) -> Optional[bytes]:
    """
    Return PNG thumbnail bytes for any supported image, or None on failure.
    For RAW files, attempts to extract embedded preview via rawpy.
    """
    filepath = Path(filepath)
    ext = filepath.suffix.lower()

    # Try rawpy for RAW formats
    if ext in RAW_EXTENSIONS:
        try:
            import rawpy  # type: ignore
            with rawpy.imread(str(filepath)) as raw:
                thumb = raw.extract_thumb()
                if thumb.format == rawpy.ThumbFormat.JPEG:
                    img = Image.open(io.BytesIO(thumb.data))
                else:
                    img = Image.fromarray(thumb.data)
        except Exception:
            img = None
    else:
        img = None

    # Fall back to Pillow for standard formats
    if img is None:
        try:
            img = Image.open(filepath)
        except Exception:
            return None

    try:
        img.thumbnail(size, Image.LANCZOS)
        # Convert to RGB so we can save as PNG regardless of input mode
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


# ── Helpers ────────────────────────────────────────────────────────────────

def is_raw(filepath: str | Path) -> bool:
    return Path(filepath).suffix.lower() in RAW_EXTENSIONS


def is_inplace_writable(filepath: str | Path) -> bool:
    return Path(filepath).suffix.lower() in INPLACE_WRITABLE


def format_exposure(value: Any) -> str:
    """Format a piexif rational shutter speed as a fraction string."""
    if isinstance(value, float):
        if value < 1:
            denom = round(1 / value)
            return f"1/{denom}s"
        return f"{value:.1f}s"
    if isinstance(value, (tuple, list)) and len(value) == 2:
        num, den = value
        if den == 0:
            return "?"
        v = num / den
        if v < 1:
            return f"1/{round(den/num)}s"
        return f"{v:.1f}s"
    return str(value)


def format_aperture(value: Any) -> str:
    """Format a rational aperture value as 'f/x.x'."""
    if isinstance(value, float):
        return f"f/{value:.1f}"
    if isinstance(value, (tuple, list)) and len(value) == 2:
        num, den = value
        if den == 0:
            return "f/?"
        return f"f/{num/den:.1f}"
    return str(value)
