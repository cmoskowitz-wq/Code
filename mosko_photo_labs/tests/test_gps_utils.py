"""
test_gps_utils.py — Mosko Photo Labs
Unit tests for GPS coordinate conversion utilities.
"""

import pytest
from app.core.gps_utils import (
    decimal_to_dms,
    dms_to_decimal,
    piexif_gps_to_decimal,
    decimal_to_piexif_gps,
    format_dms,
    format_decimal,
    parse_decimal_input,
    parse_dms_input,
    google_maps_url,
    apple_maps_url,
)


# ── decimal_to_dms ─────────────────────────────────────────────────────────

class TestDecimalToDms:
    def test_whole_degrees(self):
        d, m, s = decimal_to_dms(40.0)
        assert d == 40
        assert m == 0
        assert abs(s) < 1e-6

    def test_fractional(self):
        # 40.5° = 40° 30' 0"
        d, m, s = decimal_to_dms(40.5)
        assert d == 40
        assert m == 30
        assert abs(s) < 1e-4

    def test_nyc_latitude(self):
        # 40.7580° N
        d, m, s = decimal_to_dms(40.7580)
        assert d == 40
        assert m == 45
        assert abs(s - 28.8) < 1.0

    def test_negative_treated_as_absolute(self):
        # Function uses abs()
        d, m, s = decimal_to_dms(-73.9855)
        assert d == 73
        assert m == 59
        assert s >= 0


# ── dms_to_decimal ─────────────────────────────────────────────────────────

class TestDmsToDecimal:
    def test_north(self):
        result = dms_to_decimal(40, 30, 0, "N")
        assert abs(result - 40.5) < 1e-6

    def test_south(self):
        result = dms_to_decimal(40, 30, 0, "S")
        assert abs(result - (-40.5)) < 1e-6

    def test_east(self):
        result = dms_to_decimal(73, 59, 0, "E")
        assert result > 0

    def test_west(self):
        result = dms_to_decimal(73, 59, 0, "W")
        assert result < 0

    def test_roundtrip(self):
        original = 40.7580
        d, m, s = decimal_to_dms(original)
        back = dms_to_decimal(d, m, s, "N")
        assert abs(back - original) < 1e-4


# ── piexif GPS conversions ─────────────────────────────────────────────────

class TestPiexifGps:
    def test_piexif_to_decimal_north(self):
        # 40° 45' 0" N
        gps_tuple = ((40, 1), (45, 1), (0, 1))
        result = piexif_gps_to_decimal(gps_tuple, b"N")
        assert abs(result - 40.75) < 1e-4

    def test_piexif_to_decimal_south(self):
        gps_tuple = ((40, 1), (45, 1), (0, 1))
        result = piexif_gps_to_decimal(gps_tuple, b"S")
        assert result < 0
        assert abs(result - (-40.75)) < 1e-4

    def test_decimal_to_piexif_roundtrip(self):
        lat = 40.7580
        piexif_tuple = decimal_to_piexif_gps(lat)
        assert len(piexif_tuple) == 3
        # Each element is a (num, den) rational
        for rational in piexif_tuple:
            assert len(rational) == 2
        back = piexif_gps_to_decimal(piexif_tuple, "N")
        assert abs(back - lat) < 0.001

    def test_empty_tuple_returns_zero(self):
        assert piexif_gps_to_decimal((), "N") == 0.0
        assert piexif_gps_to_decimal(None, "N") == 0.0


# ── Formatting ─────────────────────────────────────────────────────────────

class TestFormatting:
    def test_format_dms_north(self):
        s = format_dms(40.75, is_lat=True)
        assert "N" in s
        assert "40" in s

    def test_format_dms_south(self):
        s = format_dms(-40.75, is_lat=True)
        assert "S" in s

    def test_format_dms_east(self):
        s = format_dms(73.0, is_lat=False)
        assert "E" in s

    def test_format_dms_west(self):
        s = format_dms(-73.0, is_lat=False)
        assert "W" in s

    def test_format_decimal_contains_degree(self):
        s = format_decimal(40.7580, is_lat=True)
        assert "°" in s
        assert "N" in s

    def test_format_dms_empty(self):
        assert format_dms(None, True) == ""


# ── Parsing ────────────────────────────────────────────────────────────────

class TestParsing:
    def test_parse_plain_float(self):
        assert abs(parse_decimal_input("40.7580") - 40.7580) < 1e-6

    def test_parse_negative(self):
        assert abs(parse_decimal_input("-73.9855") - (-73.9855)) < 1e-6

    def test_parse_north_suffix(self):
        result = parse_decimal_input("40.7580 N")
        assert result is not None
        assert result > 0

    def test_parse_south_suffix(self):
        result = parse_decimal_input("40.7580 S")
        assert result is not None
        assert result < 0

    def test_parse_west_suffix(self):
        result = parse_decimal_input("73.9855 W")
        assert result is not None
        assert result < 0

    def test_parse_invalid_returns_none(self):
        assert parse_decimal_input("not-a-number") is None
        assert parse_decimal_input("") is None

    def test_parse_dms_basic(self):
        result = parse_dms_input("40 45 0 N")
        assert result is not None
        assert abs(result - 40.75) < 1e-4

    def test_parse_dms_south(self):
        result = parse_dms_input("40 30 0 S")
        assert result is not None
        assert result < 0

    def test_parse_dms_insufficient_parts(self):
        assert parse_dms_input("40 45") is None


# ── URL helpers ────────────────────────────────────────────────────────────

class TestUrls:
    def test_google_maps_contains_coords(self):
        url = google_maps_url(40.7580, -73.9855)
        assert "40.758" in url
        assert "73.9855" in url

    def test_apple_maps_contains_coords(self):
        url = apple_maps_url(40.7580, -73.9855)
        assert "40.758" in url
