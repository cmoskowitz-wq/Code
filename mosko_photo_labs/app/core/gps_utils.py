"""
gps_utils.py — Mosko Photo Labs
GPS coordinate conversion utilities.
"""

from __future__ import annotations
from typing import Optional, Tuple


# ── Decimal ↔ DMS ─────────────────────────────────────────────────────────

def decimal_to_dms(decimal: float) -> Tuple[float, float, float]:
    """Convert a decimal degree value to (degrees, minutes, seconds)."""
    decimal = abs(decimal)
    degrees = int(decimal)
    minutes_float = (decimal - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    return degrees, minutes, seconds


def dms_to_decimal(degrees: float, minutes: float, seconds: float, ref: str) -> float:
    """Convert DMS + hemisphere ref to signed decimal degrees."""
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if ref.upper() in ("S", "W"):
        decimal = -decimal
    return decimal


# ── piexif ↔ decimal ──────────────────────────────────────────────────────

def piexif_rational_to_float(rational: tuple) -> float:
    """Convert a piexif rational (numerator, denominator) to float."""
    num, den = rational
    if den == 0:
        return 0.0
    return num / den


def piexif_gps_to_decimal(gps_tuple: tuple, ref: str) -> float:
    """Convert piexif GPS tuple ((d_n,d_d),(m_n,m_d),(s_n,s_d)) + ref to decimal."""
    if not gps_tuple or len(gps_tuple) < 3:
        return 0.0
    d = piexif_rational_to_float(gps_tuple[0])
    m = piexif_rational_to_float(gps_tuple[1])
    s = piexif_rational_to_float(gps_tuple[2])
    if isinstance(ref, bytes):
        ref = ref.decode("ascii", errors="ignore")
    return dms_to_decimal(d, m, s, ref)


def decimal_to_piexif_gps(decimal: float) -> tuple:
    """Convert decimal degrees to piexif GPS rational tuple."""
    d, m, s = decimal_to_dms(decimal)
    return (
        (int(d), 1),
        (int(m), 1),
        (int(round(s * 10000)), 10000),
    )


# ── Display formatting ─────────────────────────────────────────────────────

def format_dms(decimal: float, is_lat: bool) -> str:
    """Return a human-readable DMS string, e.g. '40° 26′ 46.56″ N'."""
    if decimal is None:
        return ""
    d, m, s = decimal_to_dms(decimal)
    if is_lat:
        ref = "N" if decimal >= 0 else "S"
    else:
        ref = "E" if decimal >= 0 else "W"
    return f"{d}° {m}′ {s:.2f}″ {ref}"


def format_decimal(decimal: float, is_lat: bool) -> str:
    """Return a compact decimal string like '40.446278 N'."""
    if decimal is None:
        return ""
    ref = ("N" if decimal >= 0 else "S") if is_lat else ("E" if decimal >= 0 else "W")
    return f"{abs(decimal):.6f}° {ref}"


def google_maps_url(lat: float, lon: float) -> str:
    """Return a Google Maps URL for the given coordinates."""
    return f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}"


def apple_maps_url(lat: float, lon: float) -> str:
    """Return an Apple Maps URL for the given coordinates."""
    return f"https://maps.apple.com/?q={lat:.6f},{lon:.6f}"


# ── Parsing helpers ────────────────────────────────────────────────────────

def parse_decimal_input(text: str) -> Optional[float]:
    """
    Parse user input as decimal degrees.
    Accepts: '40.4463', '-40.4463', '40.4463 N', '40.4463 S'
    Returns None if unparseable.
    """
    text = text.strip().upper()
    if not text:
        return None
    sign = 1.0
    if text.endswith(("S", "W")):
        sign = -1.0
        text = text[:-1].strip()
    elif text.endswith(("N", "E")):
        text = text[:-1].strip()
    try:
        return sign * float(text)
    except ValueError:
        return None


def parse_dms_input(text: str) -> Optional[float]:
    """
    Parse DMS input like '40 26 46.56 N' or '40°26′46.56″N'.
    Returns decimal degrees or None.
    """
    import re
    text = text.strip().upper()
    if not text:
        return None
    ref = "N"
    if text[-1] in ("N", "S", "E", "W"):
        ref = text[-1]
        text = text[:-1]
    # Extract all numbers
    parts = re.findall(r"[\d.]+", text)
    if len(parts) < 3:
        return None
    try:
        d, m, s = float(parts[0]), float(parts[1]), float(parts[2])
        return dms_to_decimal(d, m, s, ref)
    except (ValueError, IndexError):
        return None
