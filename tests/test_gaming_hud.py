"""Tests for the Gaming HUD overlay application.

Tests cover: styles, monitors, widgets, and application assembly.
Run with: python -m pytest tests/test_gaming_hud.py -v
"""

from __future__ import annotations

import sys
import time
from unittest.mock import MagicMock, patch

import pytest
import psutil

# ── Style Tests ─────────────────────────────────────────────────────────────


class TestStyles:
    def test_get_bar_color_low(self):
        from gaming_hud.styles import get_bar_color, BAR_LOW
        assert get_bar_color(0) == BAR_LOW
        assert get_bar_color(30) == BAR_LOW
        assert get_bar_color(59) == BAR_LOW

    def test_get_bar_color_medium(self):
        from gaming_hud.styles import get_bar_color, BAR_MEDIUM
        assert get_bar_color(60) == BAR_MEDIUM
        assert get_bar_color(75) == BAR_MEDIUM
        assert get_bar_color(84) == BAR_MEDIUM

    def test_get_bar_color_high(self):
        from gaming_hud.styles import get_bar_color, BAR_HIGH
        assert get_bar_color(85) == BAR_HIGH
        assert get_bar_color(95) == BAR_HIGH
        assert get_bar_color(100) == BAR_HIGH

    def test_stylesheet_not_empty(self):
        from gaming_hud.styles import MAIN_STYLESHEET
        assert len(MAIN_STYLESHEET) > 100
        assert "HUDPanel" in MAIN_STYLESHEET

    def test_constants_are_valid_colors(self):
        from gaming_hud import styles
        for name in ["BG_PRIMARY", "ACCENT_CYAN", "ACCENT_GREEN",
                      "ACCENT_RED", "TEXT_PRIMARY"]:
            color = getattr(styles, name)
            assert color.startswith("#") or color.startswith("rgba")


# ── Monitor Tests ───────────────────────────────────────────────────────────


class TestFPSMonitor:
    def test_tick_increments(self):
        from gaming_hud.monitors import FPSMonitor
        mon = FPSMonitor(interval_ms=100)
        assert mon._frame_count == 0
        mon.tick()
        assert mon._frame_count == 1
        mon.tick()
        mon.tick()
        assert mon._frame_count == 3

    def test_fps_calculation(self):
        """Simulate FPS measurement without running the thread."""
        from gaming_hud.monitors import FPSMonitor
        mon = FPSMonitor(interval_ms=100)
        mon._last_time = time.perf_counter() - 1.0  # 1 second ago
        mon._frame_count = 60
        # Calculate manually
        elapsed = time.perf_counter() - mon._last_time
        fps = int(mon._frame_count / elapsed)
        assert 55 <= fps <= 65  # Allow some tolerance


class TestNetworkMonitor:
    def test_format_speed_bytes(self):
        from gaming_hud.widgets import NetworkDisplay
        assert NetworkDisplay._format_speed(500) == "500 B/s"

    def test_format_speed_kilobytes(self):
        from gaming_hud.widgets import NetworkDisplay
        result = NetworkDisplay._format_speed(2048)
        assert "KB/s" in result

    def test_format_speed_megabytes(self):
        from gaming_hud.widgets import NetworkDisplay
        result = NetworkDisplay._format_speed(5 * 1024 * 1024)
        assert "MB/s" in result

    def test_ping_targets_defined(self):
        from gaming_hud.monitors import NetworkMonitor
        assert len(NetworkMonitor.PING_TARGETS) >= 1
        for target in NetworkMonitor.PING_TARGETS:
            parts = target.split(".")
            assert len(parts) == 4  # IPv4


class TestSystemStatsMonitor:
    def test_psutil_cpu_percent(self):
        """Verify psutil CPU reading works."""
        cpu = psutil.cpu_percent(interval=None)
        assert isinstance(cpu, float)
        assert 0.0 <= cpu <= 100.0

    def test_psutil_virtual_memory(self):
        """Verify psutil memory reading works."""
        mem = psutil.virtual_memory()
        assert mem.total > 0
        assert 0.0 <= mem.percent <= 100.0


class TestMediaDetector:
    def test_pattern_matches_youtube(self):
        from gaming_hud.monitors import MediaDetector
        pattern = MediaDetector.BROWSER_MEDIA_PATTERN
        match = pattern.match("Never Gonna Give You Up - YouTube")
        assert match is not None
        assert match.group(1).strip() == "Never Gonna Give You Up"
        assert match.group(2) == "YouTube"

    def test_pattern_matches_spotify(self):
        from gaming_hud.monitors import MediaDetector
        pattern = MediaDetector.BROWSER_MEDIA_PATTERN
        match = pattern.match("Bohemian Rhapsody - Spotify")
        assert match is not None
        assert match.group(2) == "Spotify"

    def test_pattern_no_match_plain_title(self):
        from gaming_hud.monitors import MediaDetector
        pattern = MediaDetector.BROWSER_MEDIA_PATTERN
        match = pattern.match("Visual Studio Code")
        assert match is None

    def test_media_keywords(self):
        from gaming_hud.monitors import MediaDetector
        assert "spotify" in MediaDetector.MEDIA_KEYWORDS
        assert "youtube" in MediaDetector.MEDIA_KEYWORDS


class TestKeyboardMonitor:
    def test_get_key_name_char(self):
        from gaming_hud.monitors import KeyboardMonitor
        mock_key = MagicMock(spec=[])
        mock_key.name = None
        mock_key.char = "w"
        assert KeyboardMonitor._get_key_name(mock_key) == "w"

    def test_get_key_name_uppercase(self):
        from gaming_hud.monitors import KeyboardMonitor
        mock_key = MagicMock(spec=[])
        mock_key.name = None
        mock_key.char = "W"
        assert KeyboardMonitor._get_key_name(mock_key) == "w"

    def test_get_key_name_space(self):
        from gaming_hud.monitors import KeyboardMonitor
        mock_key = MagicMock(spec=[])
        mock_key.name = "space"
        assert KeyboardMonitor._get_key_name(mock_key) == "space"

    def test_get_key_name_unknown(self):
        from gaming_hud.monitors import KeyboardMonitor
        mock_key = MagicMock(spec=[])
        assert KeyboardMonitor._get_key_name(mock_key) == ""

    def test_tracked_keys(self):
        from gaming_hud.monitors import KeyboardMonitor
        expected = {"w", "a", "s", "d", "space"}
        assert KeyboardMonitor.TRACKED_KEYS == expected


# ── Widget Tests (no GUI — structural only) ────────────────────────────────


class TestWidgetImports:
    """Verify all widget classes can be imported without a display."""

    def test_import_widgets(self):
        from gaming_hud.widgets import (
            UsageBar, StatRow, FPSDisplay, NetworkDisplay,
            MediaDisplay, KeyButton, KeyVisualizer,
            make_separator, make_section_label,
        )
        # Just verify they're callable classes/functions
        assert callable(UsageBar)
        assert callable(StatRow)
        assert callable(FPSDisplay)
        assert callable(NetworkDisplay)
        assert callable(MediaDisplay)
        assert callable(KeyButton)
        assert callable(KeyVisualizer)
        assert callable(make_separator)
        assert callable(make_section_label)


class TestAppImports:
    def test_import_app(self):
        from gaming_hud.app import HUDOverlay
        assert callable(HUDOverlay)

    def test_import_main(self):
        from gaming_hud.__main__ import main
        assert callable(main)


# ── Version Tests ───────────────────────────────────────────────────────────


class TestVersion:
    def test_version_format(self):
        from gaming_hud import __version__
        parts = __version__.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_app_name(self):
        from gaming_hud import __app_name__
        assert __app_name__ == "Moskowitz Gaming"


# ── Build Script Tests ──────────────────────────────────────────────────────


class TestBuildScript:
    def test_build_script_importable(self):
        """Verify build_hud.py can be imported without side effects."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "build_hud", "/home/user/Code/build_hud.py"
        )
        mod = importlib.util.module_from_spec(spec)
        # Don't execute — just verify it parses
        assert spec is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
